import { useEffect, useState } from "react";
import { fetchFrontendConfig } from "../utils/api";

export function useFrontendConfig(apiBase) {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [configReady, setConfigReady] = useState(false);

  useEffect(() => {
    let active = true;

    fetchFrontendConfig(apiBase)
      .then((config) => {
        if (!active) return;
        const nextModels = Array.isArray(config.availableModels) ? config.availableModels : [];
        const nextSelectedModel = config.defaultModel || nextModels[0] || "";
        setModels(nextModels);
        setSelectedModel(nextSelectedModel);
        setConfigReady(true);
      })
      .catch(() => {
        if (!active) return;
        setModels([]);
        setSelectedModel("");
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
    configReady,
  };
}
