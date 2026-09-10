const startButton = document.querySelector("#start-call");
const stopButton = document.querySelector("#stop-call");
const projectInput = document.querySelector("#project-id");
const status = document.querySelector("#call-status");
const dataStatus = document.querySelector("#data-status");
const remoteAudio = document.querySelector("#remote-audio");

const CALLS_ENDPOINT = "/api/realtime/calls";
const CALL_ID_HEADER = "X-Memo-Call-ID";
const DATA_CHANNEL_NAME = "oai-events";
const SDP_MEDIA_TYPE = "application/sdp";

let peerConnection = null;
let localStream = null;
let callId = null;

function setStatus(value) {
  status.textContent = value;
}

async function stopCall(finalStatus = "ended") {
  const closingCallId = callId;
  callId = null;
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
  startButton.disabled = false;
  stopButton.disabled = true;
  dataStatus.textContent = "Data channel: closed";
  setStatus(finalStatus);
}

async function startCall() {
  startButton.disabled = true;
  setStatus("connecting");

  try {
    const connection = new RTCPeerConnection();
    peerConnection = connection;
    connection.ontrack = (event) => {
      [remoteAudio.srcObject] = event.streams;
    };
    connection.onconnectionstatechange = () => {
      const state = connection.connectionState;
      setStatus(state === "connected" ? "listening" : state);
      if (state === "failed" || state === "closed") {
        void stopCall(state);
      }
    };

    const events = connection.createDataChannel(DATA_CHANNEL_NAME);
    events.onopen = () => {
      dataStatus.textContent = "Data channel: open";
    };
    events.onclose = () => {
      dataStatus.textContent = "Data channel: closed";
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
  } catch {
    console.error("Realtime session setup failed");
    await stopCall("failed");
  }
}

startButton.addEventListener("click", startCall);
stopButton.addEventListener("click", () => {
  void stopCall();
});
