/* 새 채팅 알림: 1분마다 안 읽은 1:1 채팅 수를 확인하고, 있으면 오른쪽 아래 버튼을 보여줍니다. */
(() => {
  const root = document.querySelector('[data-chat-alert]');
  if (!root) return;
  const button = root.querySelector('.chat-alert-button');
  const panel = root.querySelector('.chat-alert-panel');
  const list = root.querySelector('[data-chat-alert-list]');
  const count = root.querySelector('[data-chat-alert-count]');
  const menuCounts = document.querySelectorAll('[data-chat-count]');
  // 대화방 안에서는 그 대화가 이미 읽음 처리되므로 버튼을 띄우지 않습니다.
  const inChatRoom = /^\/market\/transfer\/chat\/\d+\/$/.test(location.pathname);

  const render = data => {
    const unread = data.unread || 0;
    menuCounts.forEach(el => { el.textContent = unread; el.hidden = !unread; });
    count.textContent = unread > 99 ? '99+' : unread;
    count.hidden = !unread;
    button.setAttribute('aria-label', `문의 채팅, 안 읽은 메시지 ${unread}개`);
    root.querySelector('[data-chat-alert-people]').textContent = `새 문의 ${data.unread_people || 0}명 · 대화 ${(data.items || []).length}개`;
    root.hidden = inChatRoom;
    list.replaceChildren(...(data.items || []).map(item => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = item.url;
      a.className = item.unread ? 'is-unread' : '';
      const top = document.createElement('span');
      top.className = 'chat-alert-top';
      const name = document.createElement('b'); name.textContent = item.partner;
      const at = document.createElement('small'); at.textContent = item.at;
      top.append(name, at);
      const listing = document.createElement('small'); listing.className = 'chat-alert-listing'; listing.textContent = item.listing;
      const text = document.createElement('span'); text.className = 'chat-alert-text'; text.textContent = item.text;
      a.append(top, listing, text);
      if (item.unread) { const n = document.createElement('em'); n.textContent = item.unread; a.append(n); }
      li.append(a);
      return li;
    }));
    if (!list.children.length) {
      const empty = document.createElement('li');
      empty.className = 'chat-alert-empty';
      empty.textContent = '아직 도착한 문의가 없습니다.';
      list.append(empty);
    }
  };

  const refresh = () => fetch(root.dataset.summaryUrl, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
    .then(r => r.ok ? r.json() : null).then(data => data && render(data)).catch(() => {});

  button.addEventListener('click', () => {
    const open = panel.hidden;
    panel.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
    if (open) refresh();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) { panel.hidden = true; button.setAttribute('aria-expanded', 'false'); button.focus(); } });
  document.addEventListener('click', event => {
    if (!root.contains(event.target)) { panel.hidden = true; button.setAttribute('aria-expanded', 'false'); }
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, 15000);
})();
