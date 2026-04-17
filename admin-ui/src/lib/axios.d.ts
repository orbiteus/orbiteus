import "axios";

declare module "axios" {
  interface AxiosRequestConfig {
    /** When true, global error toasts (403/404/network) are not shown. */
    skipGlobalErrorToast?: boolean;
  }
}
