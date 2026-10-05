(() => {
  const code = JSON.parse(document.getElementById("room-code").textContent);
  const me = JSON.parse(document.getElementById("me").textContent);
  const csrf = JSON.parse(document.getElementById("csrf").textContent);
  const base = `/api/room/${code}`;

  const $ = (id) => document.getElementById(id);
  const list = $("messages"), input = $("input"), form = $("composer"), sendBtn = form.querySelector("button");
  const statusEl = $("status"), peopleEl = $("people"), countEl = $("count"), typingEl = $("typing");

  let lastId = 0, lastAuthor = null, lastTypingSent = 0, busy = false;
  const seen = new Set();

  async function api(path, options = {}) {
    const res = await fetch(base + path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      ...options,
    });
    if (res.status === 401) { location.href = "/?room=" + code; throw new Error("no session"); }
    return res;
  }

  function setStatus(text, on) {
    statusEl.textContent = text;
    statusEl.classList.toggle("on", on);
  }

  // ---- polling loop: asks the server for anything new, then waits and repeats ----
  async function poll() {
    try {
      const res = await api(`/poll/?after=${lastId}`);
      if (!res.ok) throw new Error(res.status);
      const data = await res.json();
      const first = lastId === 0;

      if (first) { list.replaceChildren(); lastAuthor = null; }
      const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 120;
      data.messages.forEach((m) => addMessage(m));
      if (first && !data.messages.length) showEmpty();
      if (first || (data.messages.length && nearBottom)) list.scrollTop = list.scrollHeight;

      renderPeople(data.users);
      renderTyping(data.typing);
      setStatus("Connected", true);
    } catch (err) {
      setStatus("Reconnecting", false);
    }
    setTimeout(poll, document.hidden ? 5000 : 1500);
  }

  function showEmpty() {
    const p = document.createElement("p");
    p.className = "empty";
    p.id = "empty";
    p.textContent = "It's quiet in here. Say something, or share the invite link.";
    list.appendChild(p);
  }

  function addMessage(m) {
    if (seen.has(m.id)) return;
    seen.add(m.id);
    lastId = Math.max(lastId, m.id);
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

  function renderTyping(names) {
    typingEl.textContent = !names.length ? "" :
      names.length === 1 ? `${names[0]} is typing…` : `${names.join(", ")} are typing…`;
  }

  async function send() {
    const text = input.value.trim();
    if (!text || busy) return;
    busy = true; sendBtn.disabled = true;
    try {
      const res = await api("/send/", { method: "POST", body: JSON.stringify({ content: text }) });
      if (res.ok) {
        addMessage(await res.json());
        input.value = "";
        input.style.height = "auto";
        list.scrollTop = list.scrollHeight;
        setStatus("Connected", true);
      } else if (res.status === 403) {
        setStatus("Session expired. Reload the page.", false);
      } else if (res.status !== 429) {
        setStatus("Message not sent. Try again.", false);
      }
    } catch (err) {
      setStatus("Message not sent. Check your connection.", false);
    } finally {
      busy = false; sendBtn.disabled = false; input.focus();
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); send(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = input.scrollHeight + "px";
    const now = Date.now();
    if (now - lastTypingSent > 2000) {
      lastTypingSent = now;
      api("/typing/", { method: "POST", body: "{}" }).catch(() => {});
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

  poll();
  input.focus();
})();
