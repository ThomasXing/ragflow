/**
 * System Configuration Page
 *
 * 按照 TDD 原则：
 * 1. 先写测试（已在上面的测试文件中完成）
 * 2. 实现最小功能使测试通过
 * 3. 重构代码，保持测试通过
 *
 * 当前实现目标：通过第一个测试
 * 测试1: should render the system configuration page with tabs
 */

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Save, TestTube } from 'lucide-react';
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

// 钉钉OAuth配置表单组件（最小实现）
const DingtalkConfigForm: React.FC = () => {
  const { t } = useTranslation('translation', {
    keyPrefix: 'admin.systemConfig.dingtalk',
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">{t('appKeyLabel')}</label>
          <input
            type="text"
            className="w-full px-3 py-2 border rounded-md"
            placeholder={t('appKeyPlaceholder')}
          />
          <p className="text-sm text-muted-foreground">
            {t('appKeyDescription')}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">{t('appSecretLabel')}</label>
          <input
            type="password"
            className="w-full px-3 py-2 border rounded-md"
            placeholder={t('appSecretPlaceholder')}
          />
          <p className="text-sm text-muted-foreground">
            {t('appSecretDescription')}
          </p>
        </div>

        <div className="space-y-2 md:col-span-2">
          <label className="text-sm font-medium">{t('redirectUriLabel')}</label>
          <input
            type="url"
            className="w-full px-3 py-2 border rounded-md"
            placeholder={t('redirectUriPlaceholder')}
            defaultValue="https://example.com/oauth/callback"
          />
          <p className="text-sm text-muted-foreground">
            {t('redirectUriDescription')}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">{t('enabledLabel')}</label>
          <div className="flex items-center space-x-2">
            <input type="checkbox" id="dingtalk-enabled" defaultChecked />
            <label htmlFor="dingtalk-enabled" className="text-sm">
              {t('enabledDescription')}
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

// 默认模型配置表单组件（最小实现）
const ModelConfigForm: React.FC = () => {
  const { t } = useTranslation('translation', {
    keyPrefix: 'admin.systemConfig.model',
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">{t('providerLabel')}</label>
          <select className="w-full px-3 py-2 border rounded-md">
            <option value="openai">OpenAI</option>
            <option value="deepseek">DeepSeek</option>
            <option value="zhipu">智谱AI</option>
            <option value="azure">Azure OpenAI</option>
          </select>
          <p className="text-sm text-muted-foreground">
            {t('providerDescription')}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">{t('apiKeyLabel')}</label>
          <input
            type="password"
            className="w-full px-3 py-2 border rounded-md"
            placeholder={t('apiKeyPlaceholder')}
          />
          <p className="text-sm text-muted-foreground">
            {t('apiKeyDescription')}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">{t('baseUrlLabel')}</label>
          <input
            type="url"
            className="w-full px-3 py-2 border rounded-md"
            placeholder={t('baseUrlPlaceholder')}
            defaultValue="https://api.openai.com/v1"
          />
          <p className="text-sm text-muted-foreground">
            {t('baseUrlDescription')}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">
            {t('defaultModelLabel')}
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 border rounded-md"
            placeholder={t('defaultModelPlaceholder')}
            defaultValue="gpt-4o-mini"
          />
          <p className="text-sm text-muted-foreground">
            {t('defaultModelDescription')}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">{t('enabledLabel')}</label>
          <div className="flex items-center space-x-2">
            <input type="checkbox" id="model-enabled" defaultChecked />
            <label htmlFor="model-enabled" className="text-sm">
              {t('enabledDescription')}
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

// 主系统配置页面组件
const SystemConfigPage: React.FC = () => {
  const { t } = useTranslation('translation', {
    keyPrefix: 'admin.systemConfig',
  });
  const [activeTab, setActiveTab] = useState('dingtalk');
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  const handleSave = () => {
    setIsSaving(true);
    // TODO: 实现保存逻辑
    setTimeout(() => setIsSaving(false), 1000);
  };

  const handleValidate = () => {
    setIsValidating(true);
    // TODO: 实现验证逻辑
    setTimeout(() => setIsValidating(false), 1000);
  };

  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
        <p className="text-muted-foreground mt-2">{t('description')}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('configurationTitle')}</CardTitle>
          <CardDescription>{t('configurationDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="space-y-6"
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="dingtalk">{t('dingtalkTab')}</TabsTrigger>
              <TabsTrigger value="model">{t('modelTab')}</TabsTrigger>
            </TabsList>

            <TabsContent value="dingtalk" className="space-y-6">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">
                  {t('dingtalkSectionTitle')}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {t('dingtalkSectionDescription')}
                </p>
              </div>
              <DingtalkConfigForm />
            </TabsContent>

            <TabsContent value="model" className="space-y-6">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">
                  {t('modelSectionTitle')}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {t('modelSectionDescription')}
                </p>
              </div>
              <ModelConfigForm />
            </TabsContent>

            <div className="flex justify-end space-x-4 pt-6 border-t">
              <Button
                variant="outline"
                onClick={handleValidate}
                disabled={isValidating || isSaving}
              >
                {isValidating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('validatingButton')}
                  </>
                ) : (
                  <>
                    <TestTube className="mr-2 h-4 w-4" />
                    {t('validateButton')}
                  </>
                )}
              </Button>
              <Button onClick={handleSave} disabled={isSaving || isValidating}>
                {isSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('savingButton')}
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    {t('saveButton')}
                  </>
                )}
              </Button>
            </div>
          </Tabs>
        </CardContent>
      </Card>

      <div className="mt-8 text-sm text-muted-foreground">
        <p>{t('note')}</p>
      </div>
    </div>
  );
};

export default SystemConfigPage;
