/**
 * DingTalk OAuth登录按钮组件
 * 按照TDD原则，这个组件应该满足端到端测试的期望
 */

import { Button } from '@/components/ui/button';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { TbBrandDingtalk } from 'react-icons/tb';

interface DingtalkLoginButtonProps {
  /**
   * 是否显示按钮
   * 当钉钉OAuth配置启用时应该为true
   */
  visible?: boolean;

  /**
   * 点击回调函数
   */
  onClick?: () => void;

  /**
   * 是否正在加载
   */
  loading?: boolean;

  /**
   * 按钮文本
   */
  label?: string;
}

const DingtalkLoginButton: React.FC<DingtalkLoginButtonProps> = ({
  visible = true,
  onClick,
  loading = false,
  label,
}) => {
  const { t } = useTranslation('translation', { keyPrefix: 'login' });

  // 如果不可见，不渲染任何内容
  if (!visible) {
    return null;
  }

  const buttonText = label || t('dingtalkLogin', '登录钉钉');

  const handleClick = () => {
    if (onClick && !loading) {
      onClick();
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      className="w-full mt-4"
      onClick={handleClick}
      disabled={loading}
      data-testid="dingtalk-login-button"
    >
      {loading ? (
        <span className="flex items-center justify-center">
          <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          {t('loading', '加载中...')}
        </span>
      ) : (
        <span className="flex items-center justify-center">
          <TbBrandDingtalk className="mr-2 h-4 w-4" />
          {buttonText}
        </span>
      )}
    </Button>
  );
};

export default DingtalkLoginButton;
