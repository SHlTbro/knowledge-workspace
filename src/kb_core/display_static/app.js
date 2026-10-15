'use strict';
(function () {
  const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === keys.slice().sort().join('|');
  const text = value => typeof value === 'string' && value.trim() && !/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(value);
  const time = value => typeof value === 'string' && /T.*(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));
  const revision = value => Number.isSafeInteger(value) && value > 0;
  function safePath(value) {
    return typeof value === 'string' && value.length > 0 && !/[\\:\x00-\x1f]/.test(value) && value.split('/').every(part => part && part !== '.' && part !== '..');
  }
  function countText(count) {
    if (!count || !['asset','card','file','directory','byte'].includes(count.count_unit) || !text(count.count_scope) ||
        !(count.value === null || Number.isSafeInteger(count.value) && count.value >= 0) ||
        !(count.observed_at === null || time(count.observed_at)) || count.value !== null && count.observed_at === null) throw new Error('数量元信息无效');
    return `${count.value === null ? '未知' : count.value} ${count.count_unit} · ${count.count_scope} · ${count.observed_at === null ? '未提供采样时间' : count.observed_at}`;
  }
  function validateProjection(value) {
    if (!exact(value, ['display_schema_version','freshness','projection_revision','source_member_revision','generated_at','vaults']) || value.display_schema_version !== 'kb-display-1.1' || !['current','stale'].includes(value.freshness) || !revision(value.projection_revision) || !revision(value.source_member_revision) || !time(value.generated_at) || !Array.isArray(value.vaults)) throw new Error('发布投影无效');
    const ids = new Set();
    for (const row of value.vaults) {
      if (!exact(row, ['vault_id','member_revision','policy_revision','name','enabled','resources','counts','state']) || !['current','stale','offline','restricted'].includes(row.state) || !text(row.vault_id) || ids.has(row.vault_id) || !text(row.name) || !revision(row.member_revision) || !revision(row.policy_revision) || typeof row.enabled !== 'boolean' || !Array.isArray(row.resources) || !row.resources.every(safePath) || !Array.isArray(row.counts)) throw new Error('发布成员无效');
      ids.add(row.vault_id);
      for (const count of row.counts) { if (!exact(count, ['value','count_unit','count_scope','observed_at'])) throw new Error('数量字段无效'); countText(count); }
    }
    return value;
  }
  function validateDescription(value, id) {
    if (!exact(value, ['description_version','revision','vault_id','purpose','entry_points','structure','agent_prompt','preview_resources','counts']) || value.description_version !== '1' || !revision(value.revision) || value.vault_id !== id || !Array.isArray(value.purpose) || !value.purpose.length || !value.purpose.every(text) || !text(value.agent_prompt) || !Array.isArray(value.entry_points) || !value.entry_points.every(item => exact(item,['label','path']) && text(item.label) && safePath(item.path)) || !Array.isArray(value.structure) || !value.structure.every(safePath) || !Array.isArray(value.preview_resources) || !value.preview_resources.every(safePath) || !Array.isArray(value.counts)) throw new Error('描述元信息无效');
    for (const count of value.counts) { if (!exact(count, ['value','count_unit','count_scope','observed_at','source_ref']) || !(count.source_ref === null || safePath(count.source_ref))) throw new Error('描述数量无效'); countText(count); }
    return value;
  }
  function apiURL(kind, id, path, options = {}) {
    const sample = options.sample === true;
    const baseURL = options.baseURL || (typeof document === 'undefined' ? 'http://localhost/' : document.baseURI);
    if (sample) {
      const base = new URL('./sample-data/', baseURL);
      if (kind === 'projection') return new URL('projection.json', base).href;
      if (!['descriptions','resources'].includes(kind) || !text(id)) throw new Error('不支持的样例请求');
      if (kind === 'descriptions') return new URL(`descriptions/${encodeURIComponent(id)}.json`, base).href;
      if (!safePath(path)) throw new Error('资源路径无效');
      const suffix = path.split('/').map(encodeURIComponent).join('/');
      return new URL(`resources/${encodeURIComponent(id)}/${suffix}`, base).href;
    }
    if (kind === 'projection') return '/api/projection';
    if (!['descriptions','resources'].includes(kind) || !text(id)) throw new Error('不支持的只读请求');
    const query = new URLSearchParams({vault_id: id});
    if (kind === 'resources') { if (!safePath(path)) throw new Error('资源路径无效'); query.set('path', path); }
    return `/api/${kind}?${query}`;
  }
  async function request(kind, id, path, signal, fetcher = fetch) {
    const sample = typeof document !== 'undefined' && document.documentElement.dataset.kbPublicSample === 'true';
    const response = await fetcher(apiURL(kind,id,path,{sample}), {method:'GET', credentials:'omit', cache:'no-store', mode:'same-origin', redirect:'error', signal});
    if (!response.ok) { const error = new Error('只读请求失败'); error.status = response.status; throw error; }
    return response;
  }
  async function loadDescription(row, projection, signal, fetcher = fetch) {
    const response = await request('descriptions',row.vault_id,null,signal,fetcher);
    const sample = typeof document !== 'undefined' && document.documentElement.dataset.kbPublicSample === 'true';
    const raw = sample ? await response.clone().arrayBuffer() : null;
    const description = validateDescription(await response.json(),row.vault_id);
    if (sample) {
      const digest = await crypto.subtle.digest('SHA-256', raw);
      const rawHash = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2,'0')).join('');
      return {description,source:{binding:'sample',declared:'sample',observed:projection.generated_at,
        projectionRevision:String(projection.projection_revision),rawHash,isSample:true}};
    }
    const source = {binding:response.headers.get('X-KB-Binding-Status'), declared:response.headers.get('X-KB-Description-Status'),
      observed:response.headers.get('X-KB-Observed-At'), projectionRevision:response.headers.get('X-KB-Projection-Revision'),
      rawHash:response.headers.get('X-KB-Metadata-SHA256')};
    if (source.projectionRevision !== String(projection.projection_revision) || !/^[a-f0-9]{64}$/.test(source.rawHash || '') ||
        !time(source.observed) || !['online','offline','unbound'].includes(source.binding)) throw new Error('元信息源标记不一致');
    return {description,source};
  }
  function previewText(path, bytes) {
    if (!safePath(path) || !/\.(md|txt|json|csv|ya?ml|log|toml|ini|py|js|css)$/i.test(path) || bytes.byteLength > 256 * 1024) throw new Error('此资源不支持文本预览（上限 256 KiB）');
    const value = new TextDecoder('utf-8', {fatal:true}).decode(bytes);
    if (/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(value)) throw new Error('此资源不是可预览的 UTF-8 文本');
    return value;
  }
  function selectionGate() {
    let serial = 0;
    return {begin: id => ({id,serial:++serial}), current: ticket => ticket.serial === serial};
  }
  const api = {countText,validateProjection,validateDescription,apiURL,request,loadDescription,previewText,selectionGate};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;

  const main = document.getElementById('main-content'), gate = selectionGate();
  if (document.documentElement.dataset.kbPublicSample === 'true') {
    const banner = document.getElementById('sample-banner');
    if (banner) banner.hidden = false;
  }
  let projection = null, controller = null;
  function element(tag, value, className) { const node = document.createElement(tag); if (value !== undefined) node.textContent = value; if (className) node.className = className; return node; }
  function append(parent, ...nodes) { parent.append(...nodes); return parent; }
  function message(parent, value, error = false) { const node = element('p',value,`message${error ? ' error' : ''}`); node.setAttribute('role',error ? 'alert' : 'status'); parent.append(node); }
  function errorText(error) { return ({403:'未获准读取或权限已撤销；旧内容已清除。',404:'此资源未发布或已不存在。',503:'发布缺失、源已变化或当前不可用；请由原生入口核查。',400:'只读请求无效。'})[error.status] || '读取中断或数据无效，请重试并核查原生入口。'; }
  function start(id) { if (controller) controller.abort(); controller = new AbortController(); return gate.begin(id); }
  function heading(title, subtitle, back = false) {
    const section = element('div',undefined,'page-heading'), copy = element('div');
    if (back) { const link = element('a','← 库列表'); link.href = '#/'; copy.append(link); }
    append(copy,element('h1',title),element('p',subtitle,'muted')); section.append(copy);
    const refresh = element('button','刷新目录'); refresh.type='button'; refresh.addEventListener('click',load); section.append(refresh); main.append(section);
  }
  function counts(parent, values, compact = false) {
    if (!values.length) { parent.append(element('p','数量未声明','muted')); return; }
    for (const count of values) {
      const unit = count.count_unit === 'asset' ? '项内容' : count.count_unit === 'card' ? '张卡片' : count.count_unit === 'directory' ? '个目录' : count.count_unit === 'file' ? '个文件' : '字节';
      const label = count.value === null ? '数量未知' : `${count.value} ${unit}`;
      const node = element('p',compact ? label : `${label} · ${count.count_scope}`,'count');
      node.title = countText(count); parent.append(node);
    }
  }
  async function list(ticket) {
    heading('Vault Hub',`${projection.vaults.length} 个已发布知识库 · ${projection.freshness === 'stale' ? '目录数据等待原生入口更新' : '选择一个库，了解用途并打开可读资源'}`);
    details(main,'目录来源与新鲜度',[`发布修订 ${projection.projection_revision}`,`成员修订 ${projection.source_member_revision}`,`生成时间 ${projection.generated_at}`,'启用状态不代表正文当前可读；正文权限由每次资源请求单独裁决。']);
    if (!projection.vaults.length) { message(main,'此次发布没有展示成员。'); return; }
    const rows = element('div',undefined,'vault-list');
    const loads = [];
    projection.vaults.forEach((row,index) => {
      const line = element('article',undefined,'vault-row'), copy = element('div',undefined,'vault-copy'), link = element('a',row.name,'vault-title');
      link.href = '#/vault/' + encodeURIComponent(row.vault_id);
      const states = {current:'当前概览',stale:'历史概览',offline:'位置暂不可读',restricted:'正文范围受限'};
      append(copy,link,element('p',`${row.enabled ? states[row.state] : '成员已停用'} · ${row.vault_id}`,'vault-status'));
      const purpose = element('p','正在读取获准用途摘要…','muted'); copy.append(purpose);
      const values = element('div',undefined,'vault-counts'); counts(values,row.counts,true);
      const action = element('a','查看库信息 →','vault-action'); action.href = link.href;
      append(line,element('div',String(index+1).padStart(2,'0'),'library-icon'),copy,values,action); rows.append(line);
      loads.push((async () => {
        try {
          const loaded = await loadDescription(row,projection,controller.signal);
          if (!gate.current(ticket)) return;
          purpose.textContent = loaded.description.purpose.join('；');
        } catch (error) { if (gate.current(ticket)) purpose.textContent = '用途与接入Prompt未取得；' + errorText(error); }
      })());
    }); main.append(rows); await Promise.all(loads);
  }
  function details(parent, title, values) { const group = element('details'), summary = element('summary',title), items = element('ul'); for (const value of values) items.append(element('li',value)); append(group,summary,items); parent.append(group); }
  function promptBlock(value) {
    const prompt = element('details'); append(prompt,element('summary','接入Prompt（需确认显式本机参数）'),element('pre',value));
    const copy = element('button','复制接入Prompt'); copy.type='button';
    copy.addEventListener('click',async event => { if (!event.isTrusted || !prompt.isConnected) return; try { await navigator.clipboard.writeText(value); if (prompt.isConnected) copy.textContent='已复制文本'; } catch (_) { if (prompt.isConnected) copy.textContent='请选择上方文本手动复制'; } });
    prompt.append(copy); return prompt;
  }
  async function vault(row, ticket) {
    heading(row.name,`${row.enabled ? '已发布' : '已停用'} · ${row.state} · 只展示获准元信息与文本资源。`,true);
    const workspace = element('div',undefined,'vault-workspace'), nav = element('aside',undefined,'vault-navigation'), content = element('section',undefined,'vault-content'); append(workspace,nav,content); main.append(workspace);
    const status = element('p','正在读取单独批准的元信息…','status'); nav.append(status);
    const preview = element('section'); content.append(preview);
    let binding = 'unknown';
    try {
      const {description,source} = await loadDescription(row,projection,controller.signal);
      if (!gate.current(ticket)) return;
      binding = source.binding;
      const declared = source.declared, observed = source.observed, sourceRevision = source.projectionRevision, sourceHash = source.rawHash;
      status.textContent = `绑定：${binding} · 描述：${declared} · 历史采样：${observed}`;
      details(nav,'身份与目录来源',[`Vault ID ${row.vault_id}`,`发布于 ${projection.generated_at}`,`投影修订 ${sourceRevision}`,`${typeof document !== 'undefined' && document.documentElement.dataset.kbPublicSample === 'true' ? '样例文件' : '原始快照'} SHA256 ${sourceHash}`]);
      details(nav,'用途',description.purpose); details(nav,'原生入口（定位说明）',description.entry_points.map(item => `${item.label} · ${item.path}`)); details(nav,'结构声明',description.structure); counts(nav,description.counts);
      content.insertBefore(promptBlock(description.agent_prompt),preview);
      details(nav,'预览声明（不授予读取）',description.preview_resources);
    } catch (error) { if (!gate.current(ticket)) return; status.textContent='元信息未取得；绑定状态未知'; message(nav,errorText(error),true); }
    if (!gate.current(ticket)) return;
    content.insertBefore(element('h2','发布资源 · 文本预览'),preview);
    content.insertBefore(element('p','仅向服务器请求发布白名单中的精确资源；权限由当前 live policy 再次裁决。HTML、SVG、未知格式与二进制不预览。','muted'),preview);
    const buttons = element('ul',undefined,'resource-list');
    for (const path of row.resources) {
      const item = element('li'), button = element('button',path); button.type='button';
      const sampleMode = document.documentElement.dataset.kbPublicSample === 'true';
      button.disabled = !row.enabled || row.state === 'offline' || !sampleMode && ['offline','unbound'].includes(binding) || !/\.(md|txt|json|csv|ya?ml|log|toml|ini|py|js|css)$/i.test(path);
      button.addEventListener('click',async () => {
        const next = start(row.vault_id); preview.replaceChildren(); message(preview,'正在请求当前获准文本…');
        try { const response = await request('resources',row.vault_id,path,controller.signal); const length = response.headers.get('Content-Length'); if (length !== null && Number(length)>256*1024) throw new Error('资源超出预览上限'); const value = previewText(path,new Uint8Array(await response.arrayBuffer())); if (!gate.current(next)) return; preview.replaceChildren(element('h3',path),element('pre',value)); }
        catch (error) { if (!gate.current(next)) return; preview.replaceChildren(); message(preview,errorText(error),true); }
      }); item.append(button); buttons.append(item);
    }
    if (!row.resources.length) message(content,'此次投影未发布正文资源。'); content.insertBefore(buttons,preview);
  }
  async function load() {
    const ticket = start(location.hash); projection = null; main.replaceChildren(); main.setAttribute('aria-busy','true'); message(main,'正在读取发布投影…');
    try {
      const response = await request('projection',null,null,controller.signal), value = validateProjection(await response.json()); if (!gate.current(ticket)) return;
      projection = value; main.replaceChildren();
      if (!location.hash || location.hash === '#/') await list(ticket);
      else if (location.hash.startsWith('#/vault/')) { let id; try { id=decodeURIComponent(location.hash.slice(8)); } catch (_) { throw new Error('定位无效'); } const row=projection.vaults.find(item => item.vault_id === id); if (!row) throw Object.assign(new Error('未发布'),{status:404}); await vault(row,ticket); }
      else throw Object.assign(new Error('定位无效'),{status:400});
    } catch (error) { if (!gate.current(ticket)) return; projection=null; main.replaceChildren(); heading('知识库','只读发布当前不可用'); message(main,errorText(error),true); }
    finally { if (gate.current(ticket)) main.setAttribute('aria-busy','false'); }
  }
  window.addEventListener('hashchange',load); load();
})();
