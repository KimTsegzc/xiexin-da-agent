import { Text, View } from "@tarojs/components";
import { InteractiveAvatar } from "./InteractiveAvatar";

export function WelcomeShell({ statusText }) {
  return (
    <View className="welcome-stage">
      <View className="welcome-panel">
        <InteractiveAvatar className="hero-avatar" size="hero" />
        <View className="hero-copy">
          <Text className="welcome-title">{statusText}</Text>
        </View>
      </View>
    </View>
  );
}