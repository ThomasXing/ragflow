/**
 * Hook to check if DingTalk OAuth is enabled
 * 按照TDD原则，这个hook应该提供钉钉配置的可见性状态
 */

import { getSystemConfig } from '@/services/admin-service';
import { useQuery } from '@tanstack/react-query';

interface DingtalkConfig {
  enabled: boolean;
  app_key?: string;
  client_id?: string;
  redirect_uri?: string;
  display_name?: string;
}

const useDingtalkOAuth = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dingtalkOAuthConfig'],
    queryFn: async () => {
      try {
        // 获取钉钉OAuth配置
        const response = await getSystemConfig('dingtalk.oauth');

        if (response?.data?.code === 0 && response.data.data?.value) {
          try {
            const config = JSON.parse(response.data.data.value);
            return config as DingtalkConfig;
          } catch (parseError) {
            console.error('Failed to parse dingtalk config:', parseError);
            return null;
          }
        }
        return null;
      } catch (err) {
        console.error('Failed to fetch dingtalk config:', err);
        return null;
      }
    },
    staleTime: 5 * 60 * 1000, // 5分钟
    refetchOnWindowFocus: false,
  });

  const isEnabled = !isLoading && data?.enabled === true;
  const hasRequiredFields = data?.app_key || data?.client_id;

  return {
    // 配置数据
    config: data,
    // 是否加载中
    isLoading,
    // 错误信息
    error,
    // 钉钉OAuth是否启用
    isEnabled: isEnabled && hasRequiredFields,
    // 配置是否有效（有必要的字段）
    isValid: !isLoading && isEnabled && hasRequiredFields,
  };
};

export default useDingtalkOAuth;
