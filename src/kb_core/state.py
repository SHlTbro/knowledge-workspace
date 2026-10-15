"""Read-only derived K04 state; exact authorities and explicit observations only."""
from datetime import datetime, timezone
import json
from pathlib import Path

from .bindings import BindingError
from .contracts import CONTRACT_VERSION, ContractError, validate_contract
from .members import MemberStore, MemberStoreError
from .operations import Coordinator, OperationError

MAX_SOURCE_BYTES = 8 * 1024 * 1024


class StateError(ValueError):
    def __init__(self, code, exit_code=1):
        self.code, self.exit_code = code, exit_code
        self.message = 'Instance state check refused; inspect its declared sources.'
        super().__init__(self.message)


def _diag(source, identity, code, blocking):
    return {'source': source, 'identity': identity, 'code': code, 'blocking': blocking}


def _selection(values, namespace):
    if not isinstance(values, (list, tuple)):
        raise StateError('state_input_invalid', 2)
    selected = []
    for identity in values:
        if not isinstance(identity, str) or identity.casefold() not in namespace:
            raise StateError('state_scope_unknown')
        stable = namespace[identity.casefold()]
        if stable not in selected: selected.append(stable)
    return selected


class StateService:
    """A report is derived data, never a new member/binding authority.

    Capability flags and maintenance/display observations come from the explicit
    trusted input producer. This read-only checker does not install or run tools.
    """
    def __init__(self, instance):
        try:
            self.coordinator = Coordinator(instance)
            self.instance = self.coordinator.instance
            self.members = MemberStore(self.instance / 'members.json')
        except (BindingError, OperationError, OSError):
            raise StateError('state_instance_unavailable', 2) from None

    def _snapshot(self):
        path = self.instance / 'members.json'
        if path.exists() and path.stat().st_size > MAX_SOURCE_BYTES:
            raise StateError('state_source_limit', 2)
        return self.members.snapshot()

    @staticmethod
    def _observations(inputs):
        if not isinstance(inputs, dict) or set(inputs) != {'capabilities', 'maintenance', 'display'}:
            raise StateError('state_input_invalid', 2)
        try:
            lock = validate_contract('CapabilityLock', inputs['capabilities'])
            # The one frozen K04 source also validates the nested observation objects.
            probe = validate_contract('InstanceState', {
                'generated_at': datetime.now(timezone.utc).isoformat(), 'control_revision': 1,
                'members': [], 'capabilities': lock.model_dump()['capabilities'],
                'maintenance': inputs['maintenance'], 'display': inputs['display']})
            if probe.maintenance.status == 'ready' and (probe.maintenance.observed_at is None or not probe.maintenance.evidence_refs):
                raise StateError('state_observation_invalid', 2)
            return lock, probe.maintenance.model_dump(), probe.display.model_dump()
        except ContractError:
            raise StateError('state_observation_invalid', 2) from None

    def generate(self, inputs, *, scopes=(), required_capabilities=()):
        lock, maintenance, display = self._observations(inputs)
        try:
            # Public operation_issues checks the instance before source I/O, and
            # separates unfinished coordination from per-member availability.
            issues = self.coordinator.operation_issues()
            bindings = self.coordinator.bindings.snapshot()
            snapshot = self._snapshot()
            namespace = {identity.casefold(): row['vault_id'] for row in snapshot['records']
                         for identity in [row['vault_id'], *row['aliases']]}
            selected = _selection(scopes, namespace)
            cap_namespace = {cap.id.casefold(): cap.id for cap in lock.capabilities}
            required = _selection(required_capabilities, cap_namespace)
            diagnostics = [_diag('instance', row['operation_id'], 'state_operation_incomplete', True) for row in issues]
            observations = []
            now = datetime.now(timezone.utc).isoformat()
            for row in snapshot['records']:
                observed = self.coordinator.resolve(row['vault_id'])
                if observed['member'] != row:
                    raise StateError('state_source_changed')
                binding = observed['binding']
                if (binding['binding'] is not None and
                        (binding['binding']['vault_id'] != row['vault_id'] or binding['binding']['binding_id'] != row['location_ref'])):
                    raise StateError('state_integrity_error')
                observations.append({'member': row, 'binding': binding, 'sampled_at': now})
                if not row['enabled']:
                    diagnostics.append(_diag('member', row['vault_id'], 'member_disabled', row['vault_id'] in selected))
                if binding['status'] != 'online':
                    diagnostics.append(_diag('member', row['vault_id'], 'member_' + binding['status'], row['vault_id'] in selected))
            # Re-observe through the same public seam: a binding retarget or
            # availability change during sampling cannot leave a stale report.
            for observation in observations:
                latest = self.coordinator.resolve(observation['member']['vault_id'])
                if latest['member'] != observation['member'] or latest['binding'] != observation['binding']:
                    raise StateError('state_source_changed')
            if self._snapshot() != snapshot:
                raise StateError('state_source_changed')
            if self.coordinator.bindings.snapshot() != bindings:
                raise StateError('state_source_changed')
            # Detect newly partial operations rather than exposing a previous snapshot as clean.
            if self.coordinator.operation_issues() != issues:
                raise StateError('state_source_changed')
            for cap in lock.capabilities:
                for field, code in [('declared', 'capability_undeclared'), ('installed', 'capability_not_installed'),
                                    ('configured', 'capability_not_configured'), ('runtime_verified', 'capability_not_verified')]:
                    if not getattr(cap.verification, field):
                        diagnostics.append(_diag('capability', cap.id, code, cap.id in required))
            if maintenance['status'] != 'ready':
                diagnostics.append(_diag('maintenance', None, 'maintenance_' + maintenance['status'], False))
            if display['status'] != 'ready':
                diagnostics.append(_diag('display', None, 'display_' + display['status'], False))
            state = validate_contract('InstanceState', {
                'generated_at': now, 'control_revision': snapshot['collection_revision'],
                'members': [{'vault_id': row['vault_id'], 'revision': row['revision']} for row in snapshot['records']],
                'capabilities': lock.model_dump()['capabilities'], 'maintenance': maintenance, 'display': display}).model_dump()
            if len(json.dumps(state, ensure_ascii=False).encode('utf-8')) > MAX_SOURCE_BYTES:
                raise StateError('state_source_limit', 2)
            return {'contract_version': CONTRACT_VERSION, 'state': state,
                    'checked_scopes': selected, 'required_capabilities': required,
                    'member_observations': observations, 'diagnostics': diagnostics,
                    'check_exit_code': 1 if any(row['blocking'] for row in diagnostics) else 0}
        except MemberStoreError as error:
            if error.code in {'store_missing', 'store_io_error'}:
                raise StateError('state_source_unavailable', 2) from None
            raise StateError('state_integrity_error') from None
        except BindingError:
            # BindingStore validates its whole authority. Opaque load/path errors
            # cannot honestly be attributed to one unrelated member.
            raise StateError('state_integrity_error') from None
        except OperationError as error:
            if error.code in {'operation_instance_invalid', 'operation_io_error'}:
                raise StateError('state_source_unavailable', 2) from None
            raise StateError('state_integrity_error') from None
        except (ContractError, KeyError, TypeError, ValueError) as error:
            if isinstance(error, StateError): raise
            raise StateError('state_integrity_error') from None
        except OSError:
            raise StateError('state_source_unavailable', 2) from None

    def check(self, candidate, inputs, *, scopes=(), required_capabilities=()):
        try: candidate = validate_contract('InstanceState', candidate).model_dump()
        except ContractError: raise StateError('state_payload_invalid') from None
        report = self.generate(inputs, scopes=scopes, required_capabilities=required_capabilities)
        current = report['state']
        requested = {row['vault_id']: row['revision'] for row in candidate['members']}
        actual = {row['vault_id']: row['revision'] for row in current['members']}
        if candidate['control_revision'] != current['control_revision'] or requested != actual:
            report['diagnostics'].append(_diag('snapshot', None, 'state_member_mismatch', True))
        if ({row['id']: row for row in candidate['capabilities']} != {row['id']: row for row in current['capabilities']}
                or candidate['maintenance'] != current['maintenance']):
            report['diagnostics'].append(_diag('snapshot', None, 'state_observation_mismatch', True))
        if candidate['display'] != current['display']:
            report['diagnostics'].append(_diag('display', None, 'state_display_stale', False))
        report['check_exit_code'] = 1 if any(row['blocking'] for row in report['diagnostics']) else 0
        return report
