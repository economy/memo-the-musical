const startButton = document.querySelector("#start-call");
const stopButton = document.querySelector("#stop-call");
const demoTranscriptButton = document.querySelector("#demo-transcript");
const replayButton = document.querySelector("#replay-fallback");
const clearButton = document.querySelector("#clear-project");
const projectInput = document.querySelector("#project-id");
const status = document.querySelector("#call-status");
const dataStatus = document.querySelector("#data-status");
const remoteAudio = document.querySelector("#remote-audio");
const sessionBadge = document.querySelector("#session-badge");
const transcriptLog = document.querySelector("#transcript-log");
const dnaPanel = document.querySelector("#message-dna-panel");
const presenterRail = document.querySelector("#presenter-rail");
const hidePresenterRailButton = document.querySelector("#hide-presenter-rail");
const presetButtons = document.querySelectorAll(".preset-button");

const CALLS_ENDPOINT = "/api/realtime/calls";
const PROJECTS_ENDPOINT = "/api/projects";
const CALL_ID_HEADER = "X-Memo-Call-ID";
const DATA_CHANNEL_NAME = "oai-events";
const SDP_MEDIA_TYPE = "application/sdp";

const SECURITY_DEMO_TEXT =
  "Make our security training reminder memorable. Everyone, including contractors, " +
  "must complete LearnHub by Friday, October 16 at 5 PM Pacific. It takes about " +
  "12 minutes. Give it playful spy-movie energy, but never joke about phishing " +
  "victims. Actually, correction: Thursday, October 15—not Friday. Don't invent prizes.";

let peerConnection = null;
let localStream = null;
let callId = null;
let eventsChannel = null;
let sessionMode = "live";
let dnaPollTimer = null;
let lastDnaHtml = "";

function setStatus(value) {
  status.textContent = value;
}

function setSessionBadge(mode) {
  sessionMode = mode;
  sessionBadge.textContent = mode === "replay" ? "REPLAY" : "LIVE";
  sessionBadge.classList.toggle("bg-acid", mode === "live");
  sessionBadge.classList.toggle("text-ink", mode === "live");
  sessionBadge.classList.toggle("bg-rust", mode === "replay");
  sessionBadge.classList.toggle("text-cream", mode === "replay");
}

function appendTranscript(role, text) {
  if (!transcriptLog) {
    return;
  }
  if (transcriptLog.querySelector("li")?.textContent === "Waiting for voice…") {
    transcriptLog.innerHTML = "";
  }
  const item = document.createElement("li");
  item.textContent = `${role}: ${text}`;
  transcriptLog.appendChild(item);
  transcriptLog.scrollTop = transcriptLog.scrollHeight;
}

function refreshDnaPanel() {
  if (!dnaPanel || !projectInput?.value) {
    return;
  }
  const url = `/fragments/dna/${encodeURIComponent(projectInput.value)}`;
  fetch(url)
    .then((response) => response.text())
    .then((html) => {
      if (html === lastDnaHtml) {
        return;
      }
      lastDnaHtml = html;
      dnaPanel.innerHTML = html;
    })
    .catch(() => {
      console.warn("Message DNA refresh failed");
    });
}

function resetTranscript() {
  if (!transcriptLog) {
    return;
  }
  transcriptLog.innerHTML = '<li class="text-rust">Waiting for voice…</li>';
}

function startDnaPolling() {
  stopDnaPolling();
  refreshDnaPanel();
  dnaPollTimer = window.setInterval(refreshDnaPanel, 2500);
}

function stopDnaPolling() {
  if (dnaPollTimer !== null) {
    window.clearInterval(dnaPollTimer);
    dnaPollTimer = null;
  }
}

function handleRealtimeEvent(payload) {
  switch (payload.type) {
    case "input_audio_buffer.speech_started":
      setStatus("listening");
      break;
    case "response.created":
      setStatus("thinking");
      break;
    case "response.audio_transcript.delta":
    case "response.output_audio_buffer.started":
      setStatus("speaking");
      break;
    case "response.done":
      setStatus("listening");
      refreshDnaPanel();
      break;
    case "conversation.item.input_audio_transcription.completed":
      appendTranscript("you", payload.transcript ?? "");
      refreshDnaPanel();
      break;
    case "response.audio_transcript.done":
      appendTranscript("memo", payload.transcript ?? "");
      break;
    default:
      break;
  }
}

function sendConversationEvent(text) {
  if (!eventsChannel || eventsChannel.readyState !== "open") {
    throw new Error("Data channel is not open");
  }
  eventsChannel.send(
    JSON.stringify({
      type: "conversation.item.create",
      item: {
        type: "message",
        role: "user",
        content: [{ type: "input_text", text }],
      },
    }),
  );
  eventsChannel.send(JSON.stringify({ type: "response.create" }));
}

async function stopCall(finalStatus = "ended") {
  const closingCallId = callId;
  callId = null;
  stopDnaPolling();
  if (closingCallId) {
    try {
      await fetch(`${CALLS_ENDPOINT}/${encodeURIComponent(closingCallId)}`, {
        method: "DELETE",
      });
    } catch {
      console.warn("Sideband cleanup request failed");
    }
  }
  localStream?.getTracks().forEach((track) => track.stop());
  peerConnection?.close();
  localStream = null;
  peerConnection = null;
  eventsChannel = null;
  startButton.disabled = sessionMode === "replay";
  stopButton.disabled = true;
  demoTranscriptButton.disabled = true;
  dataStatus.textContent = "Data channel: closed";
  setStatus(finalStatus);
}

async function startCall() {
  if (sessionMode === "replay") {
    return;
  }
  startButton.disabled = true;
  setStatus("connecting");
  setSessionBadge("live");

  try {
    const connection = new RTCPeerConnection();
    peerConnection = connection;
    connection.ontrack = (event) => {
      [remoteAudio.srcObject] = event.streams;
    };
    connection.onconnectionstatechange = () => {
      const state = connection.connectionState;
      if (state === "connected") {
        setStatus("listening");
      } else if (state !== "connecting") {
        setStatus(state);
      }
      if (state === "failed" || state === "closed") {
        void stopCall(state);
      }
    };

    const events = connection.createDataChannel(DATA_CHANNEL_NAME);
    eventsChannel = events;
    events.onopen = () => {
      dataStatus.textContent = "Data channel: open";
      demoTranscriptButton.disabled = false;
    };
    events.onclose = () => {
      dataStatus.textContent = "Data channel: closed";
      demoTranscriptButton.disabled = true;
    };
    events.onmessage = (message) => {
      try {
        handleRealtimeEvent(JSON.parse(message.data));
      } catch {
        console.warn("Ignored non-JSON realtime event");
      }
    };

    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    localStream.getTracks().forEach((track) => connection.addTrack(track, localStream));

    const offer = await connection.createOffer();
    await connection.setLocalDescription(offer);
    const response = await fetch(
      `${CALLS_ENDPOINT}?project_id=${encodeURIComponent(projectInput.value)}`,
      {
        method: "POST",
        headers: { "Content-Type": SDP_MEDIA_TYPE },
        body: offer.sdp,
      },
    );
    if (!response.ok) {
      throw new Error(`Realtime setup failed (${response.status})`);
    }
    callId = response.headers.get(CALL_ID_HEADER);
    if (!callId) {
      throw new Error("Realtime setup omitted call ID");
    }
    await connection.setRemoteDescription({
      type: "answer",
      sdp: await response.text(),
    });
    stopButton.disabled = false;
    startDnaPolling();
  } catch {
    console.error("Realtime session setup failed");
    await stopCall("failed");
  }
}

async function useDemoTranscript() {
  try {
    sendConversationEvent(SECURITY_DEMO_TEXT);
    appendTranscript("you", "[demo transcript]");
    setStatus("thinking");
  } catch {
    console.error("Demo transcript send failed");
  }
}

async function clearBoard() {
  await stopCall("idle");
  const response = await fetch(`${PROJECTS_ENDPOINT}/clear`, { method: "POST" });
  if (!response.ok) {
    console.error("Clear board failed");
    return;
  }
  const payload = await response.json();
  projectInput.value = payload.project_id;
  lastDnaHtml = "";
  setSessionBadge("live");
  startButton.disabled = false;
  demoTranscriptButton.disabled = true;
  resetTranscript();
  refreshDnaPanel();
}

async function activateReplay() {
  await stopCall("idle");
  const response = await fetch(`${PROJECTS_ENDPOINT}/replay`, { method: "POST" });
  if (!response.ok) {
    console.error("Replay fallback failed");
    return;
  }
  const payload = await response.json();
  projectInput.value = payload.project_id;
  setSessionBadge("replay");
  startButton.disabled = true;
  demoTranscriptButton.disabled = true;
  refreshDnaPanel();
}

async function createPresetProject(preset) {
  const response = await fetch(PROJECTS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset }),
  });
  if (!response.ok) {
    console.error("Preset project creation failed");
    return;
  }
  const project = await response.json();
  projectInput.value = project.id;
  setSessionBadge("live");
  startButton.disabled = false;
  refreshDnaPanel();
}

startButton.addEventListener("click", () => {
  void startCall();
});
stopButton.addEventListener("click", () => {
  void stopCall();
});
demoTranscriptButton.addEventListener("click", () => {
  void useDemoTranscript();
});
replayButton.addEventListener("click", () => {
  void activateReplay();
});
clearButton?.addEventListener("click", () => {
  void clearBoard();
});
hidePresenterRailButton?.addEventListener("click", () => {
  presenterRail?.classList.add("hidden");
});
presetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    void createPresetProject(button.dataset.preset);
  });
});
