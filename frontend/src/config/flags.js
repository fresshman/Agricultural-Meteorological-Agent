/**
 * 演示形态开关——唯一接线点，功能代码一律保留。
 *
 * - `LOGIN_REQUIRED = false`：路由不再要求登录、顶栏不再出现账户菜单；
 *   `/login` 页面、`stores/auth`、后端昵称+密码接口都还在。
 *   恢复登录：这里改回 true，同时把后端环境变量 `AUTH_REQUIRED` 设为 true
 *   （否则后端仍会把无 cookie 的请求当共享访客放行，前端形同虚设）。
 * - `PERSIST_CHAT = false`：对话既不读也不写 localStorage，每次打开都是空白；
 *   偏好（流式开关/用户类型/作物）和定位照常记忆。
 *
 * 用可变对象而不是常量导出，是为了让单测能两种形态都跑一遍。
 */
export const flags = {
  LOGIN_REQUIRED: false,
  PERSIST_CHAT: false
}
