import { MutableRefObject, useCallback, useMemo, useRef } from "react";

interface ConnectOptions {
  token: string;
  sessionId: string;
}

interface RtcClientConfig {
  onLevel?: (level: number) => void;
}

interface RtcClient {
  connect: (options: ConnectOptions) => Promise<void>;
  disconnect: () => void;
}

async function createMicStream(levelCallback?: (level: number) => void): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000 }, video: false });
  if (!levelCallback) {
    return stream;
  }
  const audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 2048;
  source.connect(analyser);
  const dataArray = new Uint8Array(analyser.frequencyBinCount);

  const tick = () => {
    analyser.getByteTimeDomainData(dataArray);
    let sumSquares = 0;
    for (let i = 0; i < dataArray.length; i += 1) {
      const value = (dataArray[i] - 128) / 128;
      sumSquares += value * value;
    }
    levelCallback(Math.min(1, Math.sqrt(sumSquares / dataArray.length) * 4));
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return stream;
}

export function useRtcClient(config: RtcClientConfig = {}): RtcClient {
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const localStreamRef: MutableRefObject<MediaStream | null> = useRef(null);

  const connect = useCallback(async ({ token, sessionId }: ConnectOptions) => {
    console.debug("Connecting", { tokenLength: token.length, sessionId });
    const peer = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
    });
    peerRef.current = peer;
    const localStream = await createMicStream(config.onLevel);
    localStreamRef.current = localStream;
    localStream.getTracks().forEach((track) => peer.addTrack(track, localStream));
    // TODO: handle SDP exchange using signaling token once backend is implemented.
  }, [config.onLevel]);

  const disconnect = useCallback(() => {
    if (peerRef.current) {
      peerRef.current.getSenders().forEach((sender: RTCRtpSender) => {
        sender.track?.stop();
      });
      peerRef.current.close();
      peerRef.current = null;
    }
    if (localStreamRef.current) {
  localStreamRef.current.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      localStreamRef.current = null;
    }
  }, []);

  return useMemo(() => ({ connect, disconnect }), [connect, disconnect]);
}
