import { useEffect, useState } from "react";
import Taro from "@tarojs/taro";

export function useKeyboardHeight() {
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    let disposed = false;

    function handleKeyboardHeightChange(event) {
      setKeyboardHeight(Math.max(0, Number(event?.height) || 0));
    }

    Promise.resolve(Taro.onKeyboardHeightChange?.(handleKeyboardHeightChange)).catch(() => {
      if (!disposed) {
        setKeyboardHeight(0);
      }
    });

    return () => {
      disposed = true;
      Promise.resolve(Taro.offKeyboardHeightChange?.(handleKeyboardHeightChange)).catch(() => {});
    };
  }, []);

  return keyboardHeight;
}