export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const INFO_REACTIONS_BASE_PATH = "/api/info";
export const PROJECT_INFO_ID = "project-info-v133";
export const AVATAR_IMAGE_PATH = "/xiexin-avatar.png";
export const AVATAR_INTERACTION_VIDEO_PATH = "/smile%20face.mp4";
export const MOBILE_BREAKPOINT = 900;
export const SESSION_STORAGE_KEY = "xiexin.chat.session.v1";
export const MAX_PERSISTED_MESSAGES = 48;
export const PROJECT_INFO = {
	projectName: "谢鑫的智能体",
	developer: "广分金科部",
	version: "V13.3",
	releaseTime: "2026-04-11T02:35:00+08:00",
	features: [
		"邮件发送默认启用搜索优先增强，先检索再生成可发送正文。",
		"邮件 SMTP 失败时新增 turbo 二次解释，返回可执行修复建议。",
		"为后续 Memory 缓存取材与附件发送预留扩展挂点。",
	],
	info: "面向工作场景的企业智能问答与信息检索助手。",
	versionChange: "强化邮件内容时效性，默认先搜再发。",
};
