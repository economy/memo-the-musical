const startButton = document.querySelector("#start-call");
const stopButton = document.querySelector("#stop-call");
const projectInput = document.querySelector("#project-id");
const status = document.querySelector("#call-status");
const dataStatus = document.querySelector("#data-status");
const remoteAudio = document.querySelector("#remote-audio");

let peerConnection = null;
let localStream = null;

function setStatus(value) {
  status.textContent = value;
}

function stopCall() {
  localStream?.getTracks().forEach((track) => track.stop());
  peerConnection?.close();
  localStream = null;
  peerConnection = null;
  startButton.disabled = false;
  stopButton.disabled = true;
  dataStatus.textContent = "Data channel: closed";
  setStatus("ended");
}

async function startCall() {
  startButton.disabled = true;
  setStatus("connecting");

  try {
    peerConnection = new RTCPeerConnection();
    peerConnection.ontrack = (event) => {
      [remoteAudio.srcObject] = event.streams;
    };
    peerConnection.onconnectionstatechange = () => {
      setStatus(peerConnection.connectionState === "connected" ? "listening" : peerConnection.connectionState);
    };

    const events = peerConnection.createDataChannel("oai-events");
    events.onopen = () => {
      dataStatus.textContent = "Data channel: open";
    };
    events.onclose = () => {
      dataStatus.textContent = "Data channel: closed";
    };

    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    localStream.getTracks().forEach((track) => peerConnection.addTrack(track, localStream));

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    const response = await fetch(
      `/api/realtime/calls?project_id=${encodeURIComponent(projectInput.value)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/sdp" },
        body: offer.sdp,
      },
    );
    if (!response.ok) {
      throw new Error(`Realtime setup failed (${response.status})`);
    }
    await peerConnection.setRemoteDescription({
      type: "answer",
      sdp: await response.text(),
    });
    stopButton.disabled = false;
  } catch (error) {
    console.error(error);
    setStatus("failed");
    stopCall();
  }
}

startButton.addEventListener("click", startCall);
stopButton.addEventListener("click", stopCall);
