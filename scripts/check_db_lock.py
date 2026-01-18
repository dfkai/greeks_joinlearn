"""
检查并解决数据库锁定问题的工具脚本
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("⚠️  警告: 未安装 psutil，无法检测进程。建议运行: pip install psutil")

def find_processes_using_file(file_path: str) -> list:
    """
    查找正在使用指定文件的进程
    
    :param file_path: 文件路径
    :return: 进程信息列表
    """
    if not HAS_PSUTIL:
        return []
    
    processes = []
    abs_path = os.path.abspath(file_path)
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'open_files']):
            try:
                # 检查进程的命令行参数
                cmdline = proc.info.get('cmdline', [])
                if cmdline:
                    cmdline_str = ' '.join(cmdline).lower()
                    # 检查是否包含数据库文件名或相关脚本
                    if 'monitor.duckdb' in cmdline_str or 'run_monitor.py' in cmdline_str:
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(cmdline)
                        })
                
                # 检查打开的文件
                try:
                    open_files = proc.open_files()
                    for file_info in open_files:
                        if abs_path.lower() in file_info.path.lower():
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cmdline': ' '.join(cmdline) if cmdline else '',
                                'file': file_info.path
                            })
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"⚠️  检查进程时出错: {e}")
    
    return processes


def check_database_lock(db_path: str = "monitor.duckdb"):
    """
    检查数据库文件锁定状态
    
    :param db_path: 数据库文件路径
    """
    print("=" * 60)
    print("数据库锁定检查工具")
    print("=" * 60)
    print()
    
    # 检查文件是否存在
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    abs_db_path = os.path.abspath(db_path)
    print(f"✅ 数据库文件存在: {abs_db_path}")
    print(f"   文件大小: {os.path.getsize(db_path) / 1024:.2f} KB")
    
    # 检查 WAL 文件（Write-Ahead Log）
    wal_path = db_path + ".wal"
    if os.path.exists(wal_path):
        wal_size = os.path.getsize(wal_path)
        print(f"⚠️  发现 WAL 文件: {wal_path}")
        print(f"   WAL 文件大小: {wal_size / 1024:.2f} KB")
        if wal_size > 1024 * 1024:  # 大于1MB
            print("   ⚠️  WAL 文件较大，可能表示有未提交的事务")
    else:
        print("✅ 未发现 WAL 文件（正常）")
    
    print()
    
    # 检查是否有进程在使用数据库文件
    print("正在检查相关进程...")
    processes = find_processes_using_file(db_path)
    if processes:
        print(f"⚠️  发现 {len(processes)} 个可能使用数据库的进程：")
        for proc in processes:
            print(f"   PID: {proc['pid']}, 名称: {proc['name']}")
            if proc.get('cmdline'):
                cmdline = proc['cmdline']
                # 截断过长的命令行
                if len(cmdline) > 100:
                    cmdline = cmdline[:97] + "..."
                print(f"   命令行: {cmdline}")
        print()
    else:
        print("✅ 未发现明显使用数据库的进程")
        print()
    
    # 尝试以只读模式打开数据库
    print("正在测试数据库连接...")
    try:
        import duckdb
        conn = duckdb.connect(db_path, read_only=True)
        try:
            # 尝试执行一个简单查询
            result = conn.execute("SELECT COUNT(*) FROM position_snapshots").fetchone()
            print(f"✅ 数据库可以正常访问（只读模式）")
            print(f"   快照数量: {result[0]}")
            conn.close()
            return True
        except Exception as e:
            print(f"❌ 数据库查询失败: {e}")
            conn.close()
            return False
    except Exception as e:
        error_str = str(e).lower()
        if 'locked' in error_str or 'being used' in error_str or 'cannot open' in error_str:
            print(f"❌ 数据库文件被锁定: {e}")
            print()
            print("解决方案：")
            if processes:
                print("1. 发现相关进程，可以尝试关闭它们：")
                for proc in processes:
                    print(f"   taskkill /F /PID {proc['pid']}")
                print()
            else:
                print("1. 检查是否有其他 Python 进程在使用数据库：")
                print("   tasklist | findstr python")
                print()
                print("2. 如果发现相关进程，可以关闭它们")
                print()
            print("3. 如果问题持续，可以尝试删除 WAL 文件（如果存在）：")
            if os.path.exists(wal_path):
                print(f"   del \"{wal_path}\"")
            print()
            print("4. 重启所有相关服务")
            return False
        else:
            print(f"❌ 数据库连接失败: {e}")
            return False

def try_fix_lock(db_path: str = "monitor.duckdb", auto: bool = False):
    """
    尝试修复数据库锁定问题
    
    :param db_path: 数据库文件路径
    :param auto: 是否自动修复（不询问用户）
    """
    print("=" * 60)
    print("尝试修复数据库锁定")
    print("=" * 60)
    print()
    
    abs_db_path = os.path.abspath(db_path)
    wal_path = db_path + ".wal"
    
    # 步骤1: 检查并关闭相关进程
    processes = find_processes_using_file(db_path)
    if processes:
        print(f"发现 {len(processes)} 个可能使用数据库的进程")
        if auto or input("是否尝试关闭这些进程？(y/n): ").lower() == 'y':
            for proc in processes:
                try:
                    if HAS_PSUTIL:
                        p = psutil.Process(proc['pid'])
                        p.terminate()
                        print(f"✅ 已终止进程 PID {proc['pid']}")
                    else:
                        print(f"⚠️  需要手动关闭进程 PID {proc['pid']}")
                        print(f"   命令: taskkill /F /PID {proc['pid']}")
                except psutil.NoSuchProcess:
                    print(f"⚠️  进程 PID {proc['pid']} 已不存在")
                except psutil.AccessDenied:
                    print(f"❌ 无权限终止进程 PID {proc['pid']}，请使用管理员权限")
                except Exception as e:
                    print(f"❌ 终止进程 PID {proc['pid']} 失败: {e}")
            
            if processes:
                print("\n等待进程关闭...")
                time.sleep(2)
        else:
            print("跳过关闭进程")
        print()
    
    # 步骤2: 检查并删除 WAL 文件
    if os.path.exists(wal_path):
        wal_size = os.path.getsize(wal_path)
        print(f"发现 WAL 文件: {wal_path} (大小: {wal_size / 1024:.2f} KB)")
        
        if auto or input("是否删除 WAL 文件以尝试修复锁定？(y/n): ").lower() == 'y':
            try:
                # 先尝试重命名而不是直接删除（更安全）
                backup_path = wal_path + ".backup"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(wal_path, backup_path)
                print("✅ WAL 文件已重命名为备份文件")
                time.sleep(1)
                
                # 再次检查数据库
                if check_database_lock(db_path):
                    print("\n✅ 数据库锁定问题已解决！")
                    # 如果数据库正常，可以删除备份
                    if os.path.exists(backup_path):
                        try:
                            os.remove(backup_path)
                            print("✅ 备份文件已清理")
                        except:
                            pass
                    return True
                else:
                    print("\n❌ 问题仍然存在")
                    # 恢复 WAL 文件
                    if os.path.exists(backup_path):
                        try:
                            os.rename(backup_path, wal_path)
                            print("⚠️  已恢复 WAL 文件")
                        except:
                            pass
                    return False
            except Exception as e:
                print(f"❌ 处理 WAL 文件失败: {e}")
                return False
        else:
            print("跳过删除 WAL 文件")
    else:
        print("✅ 未发现 WAL 文件")
    
    print()
    print("请手动检查：")
    print("1. 关闭所有 Python 进程")
    print("2. 等待几秒钟")
    print("3. 重新启动应用")
    
    return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="检查数据库锁定状态")
    parser.add_argument(
        "--db-path",
        type=str,
        default="monitor.duckdb",
        help="数据库文件路径（默认: monitor.duckdb）"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="尝试修复锁定问题（交互式）"
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="自动修复锁定问题（非交互式，谨慎使用）"
    )
    
    args = parser.parse_args()
    
    if args.fix or args.auto_fix:
        success = try_fix_lock(args.db_path, auto=args.auto_fix)
        if not success:
            sys.exit(1)
    else:
        success = check_database_lock(args.db_path)
        print()
        if not success:
            print("提示：使用 --fix 参数可以尝试修复锁定问题（交互式）")
            print(f"   python scripts/check_db_lock.py --fix --db-path {args.db_path}")
            print()
            print("   或使用 --auto-fix 参数自动修复（非交互式，谨慎使用）")
            print(f"   python scripts/check_db_lock.py --auto-fix --db-path {args.db_path}")
            sys.exit(1)

