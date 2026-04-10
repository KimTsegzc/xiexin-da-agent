export const API_PORT = 8766;
export const STREAM_PATH = "/api/chat/stream";
export const CONFIG_PATH = "/api/frontend-config";
export const INFO_REACTIONS_BASE_PATH = "/api/info";
export const PROJECT_INFO_ID = "project-info-v135";
export const AVATAR_IMAGE_PATH = "/xiexin-avatar.png";
export const AVATAR_INTERACTION_VIDEO_PATH = "/smile%20face.mp4";
export const MOBILE_BREAKPOINT = 900;
export const SESSION_STORAGE_KEY = "xiexin.chat.session.v1";
export const MAX_PERSISTED_MESSAGES = 48;
export const PROJECT_INFO = {
	projectName: "谢鑫的智能体",
	developer: "广分金科部",
	version: "V13.5",
	releaseTime: "2026-04-11T04:05:00+08:00",
	features: [
		"邮件技能新增联系人目录，可将人名自动映射为邮箱地址。",
		"收件人异常统一走技能内失败解释，避免请求级编码报错直抛。",
		"等待态文案统一升级为连接中/路由中/技能运行中，并支持动名词显示。",
	],
	info: "面向工作场景的企业智能问答与信息检索助手。",
	versionChange: "增强邮件技能可用性与等待态交互一致性。",
};
