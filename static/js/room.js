(() => {
  const code = JSON.parse(document.getElementById("room-code").textContent);
  const me = JSON.parse(document.getElementById("me").textContent);

  const $ = (id) => document.getElementById(id);
  const list = $("messages"), input = $("input"), form = $("composer");
  const statusEl = $("status"), peopleEl = $("people"), countEl = $("count"), typingEl = $("typing");

  let socket, retries = 0, lastAuthor = null, lastTypingSent = 0;
  const typers = new Map(); // username -> timeout id

  function connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${scheme}://${location.host}/ws/room/${code}/`);

    socket.onopen = () => { retries = 0; setStatus("Connected", true); };
    socket.onclose = (e) => {
      if (e.code === 4401) { location.href = "/?room=" + code; return; }
      setStatus("Reconnecting", false);
      setTimeout(connect, Math.min(1000 * 2 ** retries++, 10000));
    };
    socket.onmessage = (e) => handle(JSON.parse(e.data));
  }

  function setStatus(text, on) {
    statusEl.textContent = text;
    statusEl.classList.toggle("on", on);
  }

  function handle(data) {
    if (data.type === "history") {
      list.replaceChildren();
      lastAuthor = null;
      if (!data.messages.length) showEmpty();
      data.messages.forEach((m) => addMessage(m));
      list.scrollTop = list.scrollHeight;
    } else if (data.type === "message") {
      const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 120;
      clearTyper(data.username);
      addMessage(data);
      if (nearBottom || data.username === me) list.scrollTop = list.scrollHeight;
    } else if (data.type === "presence") {
      renderPeople(data.users);
    } else if (data.type === "typing") {
      showTyper(data.username);
    }
  }

  function showEmpty() {
    const p = document.createElement("p");
    p.className = "empty";
    p.id = "empty";
    p.textContent = "It's quiet in here. Say something, or share the invite link.";
    list.appendChild(p);
  }

  function addMessage(m) {
    const empty = $("empty");
    if (empty) empty.remove();

    const mine = m.username === me;
    const row = document.createElement("div");
    row.className = "msg " + (mine ? "mine" : "theirs") + (m.username === lastAuthor ? " cont" : "");

    if (!mine && m.username !== lastAuthor) {
      const who = document.createElement("span");
      who.className = "who";
      who.textContent = m.username;
      row.appendChild(who);
    }
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = m.content; // textContent keeps messages safe from HTML injection
    row.appendChild(bubble);

    const t = document.createElement("time");
    t.dateTime = m.time;
    t.textContent = new Date(m.time).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    row.appendChild(t);

    list.appendChild(row);
    lastAuthor = m.username;
  }

  function renderPeople(users) {
    countEl.textContent = users.length;
    peopleEl.replaceChildren(...users.map((u) => {
      const li = document.createElement("li");
      li.textContent = u === me ? `${u} (you)` : u;
      return li;
    }));
  }

  function showTyper(name) {
    clearTimeout(typers.get(name));
    typers.set(name, setTimeout(() => clearTyper(name), 3000));
    renderTyping();
  }
  function clearTyper(name) {
    clearTimeout(typers.get(name));
    typers.delete(name);
    renderTyping();
  }
  function renderTyping() {
    const names = [...typers.keys()];
    typingEl.textContent = !names.length ? "" :
      names.length === 1 ? `${names[0]} is typing…` : `${names.join(", ")} are typing…`;
  }

  function send() {
    const text = input.value.trim();
    if (!text || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: "message", content: text }));
    input.value = "";
    input.style.height = "auto";
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); send(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = input.scrollHeight + "px";
    const now = Date.now();
    if (now - lastTypingSent > 2000 && socket.readyState === WebSocket.OPEN) {
      lastTypingSent = now;
      socket.send(JSON.stringify({ type: "typing" }));
    }
  });

  $("copy-link").addEventListener("click", async (e) => {
    const link = `${location.origin}/?room=${code}`;
    try { await navigator.clipboard.writeText(link); }
    catch { window.prompt("Copy this invite link:", link); return; }
    const btn = e.currentTarget, old = btn.textContent;
    btn.textContent = "Copied";
    setTimeout(() => (btn.textContent = old), 1500);
  });

  connect();
  input.focus();
})();
