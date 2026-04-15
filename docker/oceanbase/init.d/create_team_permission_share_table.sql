-- ====================================================================
-- Team Permission Share Table Migration Script for RAGFlow
-- 团队权限共享表数据库迁移脚本
--
-- This script creates the team_permission_share table in OceanBase.
-- 此脚本在OceanBase中创建team_permission_share表。
--
-- Important: This script is idempotent - it can be safely re-run.
-- 重要：此脚本是幂等的 - 可以安全地重新运行。
--
-- Change History:
-- 2026-04-15 - Created initial version for file-team-share feature
--              Created by: Thomas Xing
-- ====================================================================

-- 检查表是否存在，如果不存在则创建
CREATE TABLE IF NOT EXISTS team_permission_share (
    -- 主键ID，使用UUID格式
    id VARCHAR(32) NOT NULL COMMENT '主键ID',
    
    -- 文件/文件夹ID，关联到file表的id字段
    file_id VARCHAR(32) NOT NULL COMMENT '文件/文件夹ID',
    
    -- 租户ID，关联到tenant表的id字段
    tenant_id VARCHAR(32) NOT NULL COMMENT '租户ID',
    
    -- 权限级别：view(查看)、edit(编辑)、admin(管理员)
    permission_level VARCHAR(16) NOT NULL DEFAULT 'view' COMMENT '权限级别：view/edit/admin',
    
    -- 是否启用该共享
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否启用',
    
    -- 创建者用户ID，关联到user表的id字段
    created_by VARCHAR(32) NOT NULL COMMENT '创建者用户ID',
    
    -- 创建时间，自动填充当前时间戳
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 更新时间，自动填充当前时间戳
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 系统管理字段
    create_time BIGINT COMMENT '创建时间戳（毫秒）',
    create_date DATETIME COMMENT '创建日期',
    update_time BIGINT COMMENT '更新时间戳（毫秒）',
    update_date DATETIME COMMENT '更新日期',
    
    -- 设置主键
    PRIMARY KEY (id),
    
    -- 唯一约束：同一租户内同一文件只能有一条团队共享记录
    UNIQUE KEY uk_team_share_file_tenant (file_id, tenant_id)
    
    -- 注意：为了兼容不同数据库类型，这里不使用外键约束
    -- 应用程序层负责维护数据一致性
    
) COMMENT '团队权限共享表 - 存储文件和团队的共享权限关系';

-- 创建必要的索引以优化查询性能
-- 1. 文件ID索引（用于文件相关的查询）
CREATE INDEX IF NOT EXISTS idx_team_share_file_id ON team_permission_share(file_id);

-- 2. 租户ID索引（用于租户相关的查询）
CREATE INDEX IF NOT EXISTS idx_team_share_tenant_id ON team_permission_share(tenant_id);

-- 3. 权限级别索引（用于权限筛选查询）
CREATE INDEX IF NOT EXISTS idx_team_share_permission_level ON team_permission_share(permission_level);

-- 4. 启用状态索引（用于筛选已启用的共享）
CREATE INDEX IF NOT EXISTS idx_team_share_is_enabled ON team_permission_share(is_enabled);

-- 5. 创建者索引（用于按创建者查询）
CREATE INDEX IF NOT EXISTS idx_team_share_created_by ON team_permission_share(created_by);

-- 6. 创建时间索引（用于时间范围查询和排序）
CREATE INDEX IF NOT EXISTS idx_team_share_created_at ON team_permission_share(created_at);

-- 7. 更新时间索引（用于获取最新更新的记录）
CREATE INDEX IF NOT EXISTS idx_team_share_updated_at ON team_permission_share(updated_at);

-- 8. 复合索引：租户+启用状态（常用查询场景）
CREATE INDEX IF NOT EXISTS idx_team_share_tenant_enabled ON team_permission_share(tenant_id, is_enabled);

-- 9. 复合索引：文件+启用状态（常用查询场景）
CREATE INDEX IF NOT EXISTS idx_team_share_file_enabled ON team_permission_share(file_id, is_enabled);

-- 10. 复合索引：租户+文件+启用状态（用于快速权限检查）
CREATE INDEX IF NOT EXISTS idx_team_share_tenant_file_enabled ON team_permission_share(tenant_id, file_id, is_enabled);

-- 添加表级注释
ALTER TABLE team_permission_share COMMENT '团队权限共享表 - 用于存储租户内文件对团队的共享权限，支持权限继承';

-- 插入初始化数据示例（可根据需要启用）
-- INSERT INTO team_permission_share (id, file_id, tenant_id, permission_level, is_enabled, created_by, created_at, updated_at)
-- VALUES 
--     ('team_share_demo_001', 'file_demo_001', 'tenant_demo_001', 'view', TRUE, 'user_demo_001', NOW(), NOW()),
--     ('team_share_demo_002', 'file_demo_002', 'tenant_demo_001', 'edit', TRUE, 'user_demo_001', NOW(), NOW()),
--     ('team_share_demo_003', 'file_demo_003', 'tenant_demo_002', 'admin', TRUE, 'user_demo_002', NOW(), NOW());

-- 验证表创建成功
SELECT 'Table team_permission_share created successfully!' AS message;

-- 显示表结构（调试用）
-- SHOW CREATE TABLE team_permission_share;

-- 显示索引信息（调试用）
-- SHOW INDEX FROM team_permission_share;
