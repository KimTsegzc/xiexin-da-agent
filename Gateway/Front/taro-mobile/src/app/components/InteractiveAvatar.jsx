import { Image, View } from "@tarojs/components";
import { useEffect, useRef, useState } from "react";
import avatarImageBundled from "../../assets/xiexin-avatar.png";

const avatarImageStatic = "/static/xiexin-avatar.png";
const avatarVideoStatic = "/static/hello-there.mp4";

export function InteractiveAvatar({ className = "", size = "hero" }) {
  const [pressed, setPressed] = useState(false);
  const [avatarImage, setAvatarImage] = useState(avatarImageBundled);
  const [isPlayingVideo, setIsPlayingVideo] = useState(false);
  const [videoVisible, setVideoVisible] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.currentTime = 0;
      }
    };
  }, []);

  async function handleAvatarClick() {
    if (!videoRef.current) {
      return;
    }

    try {
      videoRef.current.currentTime = 0;
      videoRef.current.muted = false;
      await videoRef.current.play();
      setIsPlayingVideo(true);
    } catch {
      try {
        videoRef.current.currentTime = 0;
        videoRef.current.muted = true;
        await videoRef.current.play();
        setIsPlayingVideo(true);
      } catch {
        setIsPlayingVideo(false);
        setVideoVisible(false);
      }
    }
  }

  function handleVideoEnd() {
    if (!videoRef.current) {
      setIsPlayingVideo(false);
      setVideoVisible(false);
      return;
    }

    videoRef.current.pause();
    videoRef.current.currentTime = 0;
    setIsPlayingVideo(false);
    setVideoVisible(false);
  }

  return (
    <View
      className={`avatar-hitbox ${className} ${pressed ? "is-pressed" : ""} ${isPlayingVideo ? "is-playing" : ""}`}
      onTouchStart={() => setPressed(true)}
      onTouchEnd={() => setPressed(false)}
      onTouchCancel={() => setPressed(false)}
      onClick={handleAvatarClick}
    >
      <Image
        className={`avatar-media avatar-image avatar-${size}`}
        src={avatarImage}
        mode="aspectFill"
        onError={() => {
          if (avatarImage !== avatarImageStatic) {
            setAvatarImage(avatarImageStatic);
          }
        }}
      />
      <video
        ref={videoRef}
        className={`avatar-media avatar-video avatar-${size} ${videoVisible ? "is-visible" : ""}`}
        src={avatarVideoStatic}
        preload="auto"
        playsInline
        muted
        controls={false}
        autoPlay={false}
        webkit-playsinline="true"
        x5-playsinline="true"
        x5-video-player-type="h5-page"
        x5-video-orientation="portrait"
        onLoadedData={() => {
          if (isPlayingVideo) {
            setVideoVisible(true);
          }
        }}
        onPlaying={() => setVideoVisible(true)}
        onEnded={handleVideoEnd}
        onError={handleVideoEnd}
      />
    </View>
  );
}