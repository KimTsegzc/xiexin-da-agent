import { useEffect, useState } from "react";
import { fetchFrontendConfig, isClientDebugEnabled } from "../utils/api";

export function useFrontendConfig(apiBase) {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [heroWelcomeText, setHeroWelcomeText] = useState("");
  const [configReady, setConfigReady] = useState(false);

  useEffect(() => {
    let active = true;

    fetchFrontendConfig(apiBase)
      .then((config) => {
        if (!active) return;
        if (isClientDebugEnabled() && config.debug) {
          console.log("[xiexin-debug] frontend-config", config.debug);
        }
        const nextModels = Array.isArray(config.availableModels) ? config.availableModels : [];
        const nextSelectedModel = config.defaultModel || nextModels[0] || "";
        const nextHeroWelcomeText = String(config.heroWelcomeText || "").trim();
        setModels(nextModels);
        setSelectedModel(nextSelectedModel);
        setHeroWelcomeText(nextHeroWelcomeText);
        setConfigReady(true);
      })
      .catch(() => {
        if (!active) return;
        setModels([]);
        setSelectedModel("");
        setHeroWelcomeText("");
        setConfigReady(true);
      });

    return () => {
      active = false;
    };
  }, [apiBase]);

  return {
    models,
    selectedModel,
    setSelectedModel,
    heroWelcomeText,
    configReady,
  };
}
