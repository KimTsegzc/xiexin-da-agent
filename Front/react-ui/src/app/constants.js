export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const UPLOAD_PATH = "/api/uploads";
export const INFO_REACTIONS_BASE_PATH = "/api/info";
export const PROJECT_INFO_ID = "project-info-v143";
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
	version: "V14.3",
	releaseTime: "2026-04-12T13:20:00+08:00",
	features: [
		"聊天支持上传图片与文件，服务端统一落库到 shared_space 并注入对话上下文。",
		"上传场景默认切换到 qwen3-omni-flash，修正模型名大小写导致的 404 问题。",
		"前端上传入口收口为仅支持图片，并对非图片给出明确提示。",
	],
	info: "面向工作场景的企业智能问答与信息检索助手。",
	versionChange: "收口多模态上传范围，当前仅支持图片解析。",
};
