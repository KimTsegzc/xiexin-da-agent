const path = require("path");

const config = {
  projectName: "xiexin-taro-mobile",
  date: "2026-03-27",
  designWidth: 375,
  deviceRatio: {
    375: 2,
    750: 1,
  },
  sourceRoot: "src",
  outputRoot: "dist",
  plugins: [],
  defineConstants: {},
  copy: {
    patterns: [
      {
        from: path.resolve(__dirname, "../static/xiexin-avatar.png"),
        to: "static/xiexin-avatar.png",
      },
      {
        from: path.resolve(__dirname, "../static/hello-there.mp4"),
        to: "static/hello-there.mp4",
      },
    ],
    options: {},
  },
  framework: "react",
  compiler: "webpack5",
  cache: {
    enable: false,
  },
  mini: {},
  h5: {
    publicPath: "/",
    staticDirectory: "static",
    devServer: {
      host: "0.0.0.0",
      port: 8501,
      hot: true,
    },
  },
};

module.exports = function mergeConfig() {
  return config;
};
