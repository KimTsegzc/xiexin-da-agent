export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const UPLOAD_PATH = "/api/uploads";
export const INFO_REACTIONS_BASE_PATH = "/api/info";
export const PROJECT_INFO_ID = "project-info-v150";
export const AVATAR_IMAGE_PATH = "/xiexin-avatar.png";
export const AVATAR_INTERACTION_VIDEO_PATH = "/smile%20face.mp4";
export const MOBILE_BREAKPOINT = 900;
export const SESSION_STORAGE_KEY = "xiexin.chat.session.v1";
export const MAX_PERSISTED_MESSAGES = 48;
export const UPLOAD_OMNI_MODEL = "qwen3-omni-flash";
export const PROJECT_SKILL_SET = [
	"skill-direct-chat",
	"skill-ccb-get-handler",
	"skill-send-email",
];
export const PROJECT_INFO = {
	projectName: "谢鑫的智能体",
	developer: "广分金科部",
	version: "V15.0",
	releaseTime: "2026-04-13T10:30:00+08:00",
	features: [
		"邮件技能支持多人收件人，并在真正发送前增加收件人二次确认，避免误打扰。",
		"LLM 请求统一补入当天日期与当前时间的 system 贴尾，直接对话与技能链路一致。",
		"职能查询链路补强负责人链条渲染、领导岗提示与提示词约束，返回更贴近实际使用口径。",
		"Prompt 与联系人配置同步更新，身份口径、联系人映射和邮件尾注进一步统一。",
	],
	info: "面向工作场景的企业智能问答与信息检索助手。",
	versionChange: "统一整理邮件确认、多收件人、时间 system 贴尾与职能查询响应。",
};
