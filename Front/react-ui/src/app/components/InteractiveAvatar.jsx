import { useEffect, useRef, useState } from "react";
import { AVATAR_IMAGE_PATH, AVATAR_INTERACTION_VIDEO_PATH } from "../constants";

export function InteractiveAvatar({ className, alt, ariaLabel }) {
  const [playing, setPlaying] = useState(false);
  const [videoVisible, setVideoVisible] = useState(false);
  const videoRef = useRef(null);
  const resetTimerRef = useRef(null);

  useEffect(() => () => {
    if (resetTimerRef.current) {
      window.clearTimeout(resetTimerRef.current);
    }
  }, []);

  useEffect(() => {
    if (!playing || !videoRef.current) return;
    if (resetTimerRef.current) {
      window.clearTimeout(resetTimerRef.current);
      resetTimerRef.current = null;
    }

    async function startPlayback() {
      if (!videoRef.current) return;
      videoRef.current.currentTime = 0;
      videoRef.current.muted = false;
      videoRef.current.volume = 1;
      try {
        await videoRef.current.play();
      } catch {
        try {
          if (!videoRef.current) return;
          videoRef.current.currentTime = 0;
          videoRef.current.muted = true;
          await videoRef.current.play();
        } catch {
          setPlaying(false);
          setVideoVisible(false);
        }
      }
    }

    void startPlayback();
  }, [playing]);

  function handleClick() {
    if (resetTimerRef.current) {
      window.clearTimeout(resetTimerRef.current);
      resetTimerRef.current = null;
    }
    if (playing && videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.muted = false;
      void videoRef.current.play();
      return;
    }
    setPlaying(true);
  }

  function handleVideoEnded() {
    setVideoVisible(false);
    resetTimerRef.current = window.setTimeout(() => {
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      }
      setPlaying(false);
      resetTimerRef.current = null;
    }, 160);
  }

  return (
    <button
      type="button"
      className={`avatar-hitbox ${className}`}
      onClick={handleClick}
      aria-label={ariaLabel || alt || "头像互动"}
    >
      <img className="avatar-media avatar-image" src={AVATAR_IMAGE_PATH} alt={alt} />
      <video
        ref={videoRef}
        className={`avatar-media avatar-video ${videoVisible ? "is-visible" : ""}`}
        src={AVATAR_INTERACTION_VIDEO_PATH}
        preload="auto"
        playsInline
        webkit-playsinline="true"
        onLoadedData={() => {
          if (playing) {
            setVideoVisible(true);
          }
        }}
        onPlaying={() => setVideoVisible(true)}
        onEnded={handleVideoEnded}
      />
    </button>
  );
}
