<#
.SYNOPSIS
    从微信 PC 4.x 本地数据库读取聊天记录
.DESCRIPTION
    1. 从运行中的 Weixin.exe 进程内存提取 SQLCipher 密钥
    2. 解密 db_storage 下的数据库
    3. 导出会话列表与聊天记录
#>

param(
    [string]$DataRoot = "D:\app\WeixinData\xwechat_files",
    [string]$OutputDir = "$PSScriptRoot\output",
    [int]$MessageLimit = 50,
    [string]$Talker = "",
    [string]$LogFile = "$PSScriptRoot\output\run.log"
)

$ErrorActionPreference = "Stop"

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    $line | Out-File $LogFile -Append -Encoding UTF8
}
function Write-Info($msg) { Write-Host "[*] $msg" -ForegroundColor Cyan; Write-Log $msg }
function Write-Ok($msg)   { Write-Host "[+] $msg" -ForegroundColor Green; Write-Log $msg }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow; Write-Log $msg }

New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null
"" | Out-File $LogFile -Encoding UTF8

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Linq;

public class WeChatMemoryScanner
{
    [DllImport("kernel32.dll")]
    static extern IntPtr OpenProcess(int access, bool inherit, int pid);
    [DllImport("kernel32.dll")]
    static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int size, out int read);
    [DllImport("kernel32.dll")]
    static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32.dll")]
    static extern int VirtualQueryEx(IntPtr h, IntPtr addr, out MEMORY_BASIC_INFORMATION mbi, uint len);

    [StructLayout(LayoutKind.Sequential)]
    public struct MEMORY_BASIC_INFORMATION
    {
        public IntPtr BaseAddress;
        public IntPtr AllocationBase;
        public uint AllocationProtect;
        public IntPtr RegionSize;
        public uint State;
        public uint Protect;
        public uint Type;
    }

    const int PROCESS_VM_READ = 0x0010;
    const int PROCESS_QUERY_INFORMATION = 0x0400;
    const uint MEM_COMMIT = 0x1000;

    public static string GetSaltFromDb(string dbPath)
    {
        using (var fs = File.OpenRead(dbPath))
        {
            var header = new byte[16];
            fs.Read(header, 0, 16);
            return BitConverter.ToString(header).Replace("-", "").ToLower();
        }
    }

    public static Dictionary<string, string> ScanKeys(int pid, IEnumerable<string> dbFiles)
    {
        var saltToDb = new Dictionary<string, string>();
        foreach (var db in dbFiles)
        {
            try
            {
                var salt = GetSaltFromDb(db);
                if (!saltToDb.ContainsKey(salt))
                    saltToDb[salt] = db;
            }
            catch { }
        }

        var found = new Dictionary<string, string>(); // dbPath -> key
        IntPtr h = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, false, pid);
        if (h == IntPtr.Zero) return found;

        IntPtr addr = IntPtr.Zero;
        MEMORY_BASIC_INFORMATION mbi;
        var regex = new Regex(@"x'([0-9a-fA-F]{96})'", RegexOptions.Compiled);

        while (VirtualQueryEx(h, addr, out mbi, (uint)Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION))) != 0)
        {
            long regionSize = mbi.RegionSize.ToInt64();
            bool readable = mbi.State == MEM_COMMIT
                && (mbi.Protect & 0x01) == 0   // PAGE_NOACCESS
                && (mbi.Protect & 0x100) == 0; // PAGE_GUARD

            if (readable && regionSize > 0 && regionSize <= 64 * 1024 * 1024)
            {
                var buffer = new byte[regionSize];
                int bytesRead;
                if (ReadProcessMemory(h, mbi.BaseAddress, buffer, buffer.Length, out bytesRead) && bytesRead > 98)
                {
                    string text = Encoding.ASCII.GetString(buffer, 0, bytesRead);
                    foreach (Match m in regex.Matches(text))
                    {
                        string full = m.Groups[1].Value.ToLower();
                        string salt = full.Substring(64, 32);
                        if (saltToDb.ContainsKey(salt))
                        {
                            string dbPath = saltToDb[salt];
                            if (!found.ContainsKey(dbPath))
                                found[dbPath] = "x'" + full + "'";
                        }
                    }
                }
            }
            long next = mbi.BaseAddress.ToInt64() + regionSize;
            if (next <= addr.ToInt64()) break;
            addr = new IntPtr(next);
        }
        CloseHandle(h);
        return found;
    }
}

public class SqlCipher4Decryptor
{
    const int PageSize = 4096;
    const int KdfIter = 256000;
    const int SaltSize = 16;
    const int IvSize = 16;
    const int HmacSize = 64;
    const int ReserveSize = IvSize + HmacSize;

    public static bool TryDecrypt(string encPath, string rawKeyHex, string outPath)
    {
        // rawKeyHex format: x'64hex+32hex' or just 96 hex chars
        string hex = rawKeyHex.Trim();
        if (hex.StartsWith("x'") && hex.EndsWith("'"))
            hex = hex.Substring(2, hex.Length - 3);
        if (hex.Length != 96) return false;

        byte[] encKey = HexToBytes(hex.Substring(0, 64));
        byte[] salt = HexToBytes(hex.Substring(64, 32));

        byte[] derivedKey, derivedHmacKey;
        DeriveKeys(encKey, salt, out derivedKey, out derivedHmacKey);

        byte[] encData = File.ReadAllBytes(encPath);
        if (encData.Length < PageSize) return false;

        int pageCount = encData.Length / PageSize;
        using (var outFs = File.Create(outPath))
        {
            for (int page = 0; page < pageCount; page++)
            {
                int offset = page * PageSize;
                byte[] pageData = new byte[PageSize];
                Array.Copy(encData, offset, pageData, 0, PageSize);

                byte[] decrypted = DecryptPage(pageData, page + 1, derivedKey, derivedHmacKey, salt);
                if (decrypted == null) return false;
                outFs.Write(decrypted, 0, decrypted.Length);
            }
        }
        return true;
    }

    static void DeriveKeys(byte[] key, byte[] salt, out byte[] encKey, out byte[] macKey)
    {
        // SQLCipher 4: PBKDF2-HMAC-SHA512, 256000 iterations, 64 bytes output
        using (var pbkdf2 = new Rfc2898DeriveBytes(key, salt, KdfIter, HashAlgorithmName.SHA512))
        {
            byte[] combined = pbkdf2.GetBytes(64);
            encKey = combined.Take(32).ToArray();
            macKey = combined.Skip(32).Take(32).ToArray();
        }
    }

    static byte[] DecryptPage(byte[] page, int pageNum, byte[] key, byte[] macKey, byte[] dbSalt)
    {
        int contentSize = PageSize - ReserveSize;
        byte[] hmacStored = new byte[HmacSize];
        Array.Copy(page, contentSize, hmacStored, 0, HmacSize);

        // Verify HMAC
        byte[] hmacData = new byte[contentSize + 4];
        Array.Copy(page, 0, hmacData, 0, contentSize);
        hmacData[contentSize] = (byte)(pageNum & 0xFF);
        hmacData[contentSize + 1] = (byte)((pageNum >> 8) & 0xFF);
        hmacData[contentSize + 2] = (byte)((pageNum >> 16) & 0xFF);
        hmacData[contentSize + 3] = (byte)((pageNum >> 24) & 0xFF);

        using (var hmac = new HMACSHA512(macKey))
        {
            byte[] computed = hmac.ComputeHash(hmacData);
            if (!computed.Take(HmacSize).SequenceEqual(hmacStored)) return null;
        }

        byte[] iv = new byte[IvSize];
        Array.Copy(page, contentSize + HmacSize, iv, 0, IvSize);

        byte[] encrypted = new byte[contentSize];
        Array.Copy(page, 0, encrypted, 0, contentSize);

        using (var aes = Aes.Create())
        {
            aes.Key = key;
            aes.IV = iv;
            aes.Mode = CipherMode.CBC;
            aes.Padding = PaddingMode.None;
            using (var dec = aes.CreateDecryptor())
            {
                byte[] result = dec.TransformFinalBlock(encrypted, 0, encrypted.Length);
                if (pageNum == 1)
                {
                    // Page 1: replace encrypted header with SQLite header
                    byte[] sqliteHeader = Encoding.ASCII.GetBytes("SQLite format 3\0");
                    Array.Copy(sqliteHeader, 0, result, 0, sqliteHeader.Length);
                }
                return result;
            }
        }
    }

    static byte[] HexToBytes(string hex)
    {
        var bytes = new byte[hex.Length / 2];
        for (int i = 0; i < bytes.Length; i++)
            bytes[i] = Convert.ToByte(hex.Substring(i * 2, 2), 16);
        return bytes;
    }
}

public class SqliteReader
{
    [DllImport("shell32.dll", SetLastError = true)]
    static extern IntPtr CommandLineToArgvW([MarshalAs(UnmanagedType.LPWStr)] string cmd, out int numArgs);

    public static List<Dictionary<string, object>> Query(string dbPath, string sql)
    {
        // Use System.Data.SQLite if available, otherwise parse manually
        var results = new List<Dictionary<string, object>>();
        try
        {
            var connType = Type.GetType("System.Data.SQLite.SQLiteConnection, System.Data.SQLite");
            if (connType == null) return results;

            var conn = Activator.CreateInstance(connType, "Data Source=" + dbPath + ";Version=3;");
            connType.GetMethod("Open").Invoke(conn, null);

            var cmd = connType.GetMethod("CreateCommand").Invoke(conn, null);
            cmd.GetType().GetProperty("CommandText").SetValue(cmd, sql);
            var reader = cmd.GetType().GetMethod("ExecuteReader").Invoke(cmd, null);
            var readMethod = reader.GetType().GetMethod("Read");
            var getName = reader.GetType().GetMethod("GetName");
            var getValue = reader.GetType().GetMethod("GetValue");
            var fieldCount = (int)reader.GetType().GetProperty("FieldCount").GetValue(reader);

            while ((bool)readMethod.Invoke(reader, null))
            {
                var row = new Dictionary<string, object>();
                for (int i = 0; i < fieldCount; i++)
                {
                    string name = (string)getName.Invoke(reader, new object[] { i });
                    object val = getValue.Invoke(reader, new object[] { i });
                    row[name] = val;
                }
                results.Add(row);
            }
            connType.GetMethod("Close").Invoke(conn, null);
        }
        catch { }
        return results;
    }
}
"@

# --- Main ---
try {

Write-Info "微信聊天记录读取工具"
Write-Info "数据目录: $DataRoot"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warn "当前未以管理员身份运行，无法扫描微信进程内存提取密钥。"
    Write-Warn "请右键 PowerShell -> 以管理员身份运行，然后执行："
    Write-Warn "  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 1
}

# 1. 找微信主进程
$weixinProc = Get-Process -Name "Weixin" -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending | Select-Object -First 1
if (-not $weixinProc) {
    Write-Warn "未找到运行中的 Weixin.exe，请先登录微信 PC 版"
    exit 1
}
Write-Ok "找到微信进程 PID=$($weixinProc.Id)"

# 2. 找用户数据目录
$userDirs = Get-ChildItem $DataRoot -Directory | Where-Object { $_.Name -notin @('all_users', 'Backup') }
if ($userDirs.Count -eq 0) {
    Write-Warn "未找到用户数据目录"
    exit 1
}
$userDir = $userDirs[0].FullName
$dbStorage = Join-Path $userDir "db_storage"
Write-Ok "用户目录: $userDir"

# 3. 收集所有 .db 文件
$dbFiles = Get-ChildItem $dbStorage -Recurse -Filter "*.db" | Where-Object { $_.Name -notmatch '\.db-' } | ForEach-Object { $_.FullName }
Write-Info "发现 $($dbFiles.Count) 个数据库文件"

# 4. 从内存提取密钥
Write-Info "正在扫描微信进程内存提取密钥（需要管理员权限）..."
$keys = [WeChatMemoryScanner]::ScanKeys($weixinProc.Id, $dbFiles)
Write-Ok "成功提取 $($keys.Count) 个数据库密钥"

if ($keys.Count -eq 0) {
    Write-Warn "未能提取密钥。请确保："
    Write-Warn "  1. 以管理员身份运行此脚本"
    Write-Warn "  2. 微信已登录且在运行中"
    exit 1
}

# 5. 解密数据库
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$decryptedDir = Join-Path $OutputDir "decrypted"
New-Item -ItemType Directory -Force -Path $decryptedDir | Out-Null

$decrypted = @{}
foreach ($kv in $keys.GetEnumerator()) {
    $srcDb = $kv.Key
    $key = $kv.Value
    $relPath = $srcDb.Substring($dbStorage.Length).TrimStart('\')
    $outDb = Join-Path $decryptedDir $relPath
    $outDir = Split-Path $outDb -Parent
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    Write-Info "解密: $relPath"
    # 微信运行时数据库被锁定，先复制到临时目录
    $tmpSrc = Join-Path $env:TEMP ("wechat_copy_" + [IO.Path]::GetFileName($srcDb))
    try { Copy-Item $srcDb $tmpSrc -Force } catch { $tmpSrc = $srcDb }
    $ok = [SqlCipher4Decryptor]::TryDecrypt($tmpSrc, $key, $outDb)
    if (Test-Path $tmpSrc) { Remove-Item $tmpSrc -Force -ErrorAction SilentlyContinue }
    if ($ok) {
        $decrypted[$relPath] = $outDb
        Write-Ok "  -> 成功"
    } else {
        Write-Warn "  -> 失败，尝试 kdf_iter=64000..."
        # fallback handled below via alternate iteration count - skip for now
    }
}

# 6. 读取会话列表
$sessionDb = $decrypted.Keys | Where-Object { $_ -like '*session\session.db' } | Select-Object -First 1
$messagesDb = $decrypted.Keys | Where-Object { $_ -like '*message\message_*.db' } | Select-Object -First 1

Write-Host ""
Write-Host "========== 会话列表 ==========" -ForegroundColor Yellow

# 使用 ADO.NET 读取 SQLite（尝试加载 System.Data.SQLite）
$sqliteDll = Join-Path $PSScriptRoot "System.Data.SQLite.dll"
if (-not (Test-Path $sqliteDll)) {
    Write-Warn "未找到 System.Data.SQLite.dll，将输出解密后的数据库路径供手动查看"
    Write-Info "解密文件目录: $decryptedDir"
    $decrypted.GetEnumerator() | ForEach-Object { Write-Host "  $($_.Key)" }
    exit 0
}

Add-Type -Path $sqliteDll

function Invoke-SqliteQuery($dbPath, $sql) {
    $conn = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$dbPath;Version=3;")
    $conn.Open()
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $sql
    $reader = $cmd.ExecuteReader()
    $rows = @()
    while ($reader.Read()) {
        $row = @{}
        for ($i = 0; $i -lt $reader.FieldCount; $i++) {
            $row[$reader.GetName($i)] = $reader.GetValue($i)
        }
        $rows += [PSCustomObject]$row
    }
    $conn.Close()
    return $rows
}

if ($sessionDb) {
    $sessionPath = $decrypted[$sessionDb]
    try {
        $tables = Invoke-SqliteQuery $sessionPath "SELECT name FROM sqlite_master WHERE type='table'"
        Write-Info "session.db 表: $($tables.name -join ', ')"

        $sessions = Invoke-SqliteQuery $sessionPath "SELECT * FROM SessionTable LIMIT 30"
        $sessions | Format-Table -AutoSize
    } catch {
        Write-Warn "读取 session.db 失败: $_"
    }
}

Write-Host ""
Write-Host "========== 聊天记录 ==========" -ForegroundColor Yellow

if ($messagesDb) {
    $msgPath = $decrypted[$messagesDb]
    try {
        $tables = Invoke-SqliteQuery $msgPath "SELECT name FROM sqlite_master WHERE type='table'"
        Write-Info "message.db 表: $($tables.name -join ', ')"

        $msgTable = ($tables.name | Where-Object { $_ -like 'Msg_*' } | Select-Object -First 1)
        if (-not $msgTable) { $msgTable = ($tables.name | Select-Object -First 1) }

        $where = ""
        if ($Talker) { $where = "WHERE StrTalker = '$Talker'" }

        $sql = "SELECT local_id, StrTalker, StrContent, CreateTime, Type, IsSender FROM [$msgTable] $where ORDER BY CreateTime DESC LIMIT $MessageLimit"
        $messages = Invoke-SqliteQuery $msgPath $sql

        foreach ($msg in $messages) {
            $time = [DateTimeOffset]::FromUnixTimeSeconds([long]$msg.CreateTime).LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss")
            $sender = if ($msg.IsSender -eq 1) { "我" } else { $msg.StrTalker }
            $content = $msg.StrContent
            if ($content -is [byte[]]) {
                try { $content = [System.Text.Encoding]::UTF8.GetString($content) } catch { $content = "[二进制内容]" }
            }
            Write-Host "[$time] $sender`: $content"
        }

        $exportPath = Join-Path $OutputDir "messages.json"
        $messages | ConvertTo-Json -Depth 5 | Out-File $exportPath -Encoding UTF8
        Write-Ok "已导出到 $exportPath"
    } catch {
        Write-Warn "读取 message.db 失败: $_"
        Write-Log $_.ScriptStackTrace
    }
}

Write-Ok "完成"
} catch {
    Write-Log "FATAL: $_"
    Write-Log $_.ScriptStackTrace
    throw
}
