import { Text, View } from "@tarojs/components";
import { Cell, Dialog, Popup, Tag, Toast } from "react-vant";

export function SettingsControl({
  open,
  models,
  selectedModel,
  onOpen,
  onClose,
  onSelect,
  onNewChat,
  chatMode,
}) {
  async function handleSelectModel(model) {
    if (model === selectedModel) {
      Toast.info({ message: "当前已是该模型" });
      return;
    }

    onSelect(model);
    Toast.success({ message: `已切换到 ${model}` });
  }

  async function handleNewChat() {
    try {
      await Dialog.confirm({
        title: "开始新对话",
        message: "将清空当前移动端会话记录，是否继续？",
      });
      onNewChat();
      Toast.success({ message: "已开始新对话" });
    } catch {
      // Ignore cancelled actions.
    }
  }

  return (
    <View className="settings-anchor">
      <View
        className={`settings-toggle ${open ? "is-open" : ""}`}
        role="button"
        aria-label={open ? "关闭模型侧边栏" : "打开模型侧边栏"}
        onClick={open ? onClose : onOpen}
      >
        <View />
        <View />
        <View />
      </View>

      <Popup
        visible={open}
        position="right"
        zIndex={30}
        className="settings-drawer-popup"
        overlayClass="settings-drawer-overlay"
        closeOnClickOverlay
        safeAreaInsetBottom
        onClose={onClose}
      >
        <View className="settings-drawer">
          <View className="settings-drawer-header">
            <Text className="settings-drawer-eyebrow">MODEL</Text>
            <Text className="settings-drawer-title">模型列表</Text>
            <Text className="settings-drawer-copy">
              {selectedModel ? `当前使用：${selectedModel}` : "选择一个模型开始对话"}
            </Text>
          </View>

          <View className="settings-drawer-body">
            {models.length ? (
              <View className="settings-list">
                {models.map((model) => {
                  const isSelected = model === selectedModel;

                  return (
                    <Cell
                      key={model}
                      border={false}
                      clickable
                      className={`settings-cell ${isSelected ? "is-selected" : ""}`}
                      title={(
                        <View className="settings-cell-title-row">
                          <Text className="settings-cell-name">{model}</Text>
                          {isSelected ? (
                            <Tag className="settings-cell-tag" round plain type="primary">
                              当前
                            </Tag>
                          ) : null}
                        </View>
                      )}
                      label={isSelected ? "已用于当前对话" : "点击切换到这个模型"}
                      onClick={() => handleSelectModel(model)}
                    />
                  );
                })}
              </View>
            ) : (
              <View className="settings-empty-state">
                <Text className="settings-empty-title">暂无可选模型</Text>
                <Text className="settings-empty-copy">前端配置还没返回模型列表，稍后再试。</Text>
              </View>
            )}
          </View>

          {chatMode ? (
            <View className="settings-drawer-footer">
              <View className="settings-newchat" role="button" onClick={handleNewChat}>
                <Text className="settings-newchat-label">开启新对话</Text>
                <Text className="settings-newchat-copy">清空当前移动端会话记录</Text>
              </View>
            </View>
          ) : null}
        </View>
      </Popup>
    </View>
  );
}