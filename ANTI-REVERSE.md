# 模组工坊 · 防逆向 / 防 AI 改写 / 防盗版 / 反倒卖

> 交付对象：`_out/AoE2ModWorkshop-sealed/`
> 门禁：`python -X utf8 _probe/verify_sealed.py --app _out/AoE2ModWorkshop-sealed/app`
> 收尾行：`SEALED BUNDLE: ALL CHECKS OK`

产品开源免费，所以目标不是"让人用不了"，而是四件事：

1. **拿不到可读源码** —— 逆向成本从"解压即得"抬到"自己写一个解包器"；
2. **改一个字节就跑不起来** —— 改包不再是"改完就能转发"；
3. **多出来的文件也不收** —— 丢一个 `sitecustomize.py` 进来同样拒绝；
4. **每次构建带指纹** —— 谁流出去的能对上号，转发的人删不干净。

授权（绑机器）是**可选**的一层，默认关：`--free` 出的包不验授权。
绑机器对开源免费项目没有意义 —— 玩家把包拷到第二台电脑不是敌人。但完整性
校验必须留，因为"改过的包冒充原版"才是要防的那件事。

---

## 一、分层结构（谁挡什么）

| 层 | 位置 | 挡住什么 | 挡不住什么 |
|---|---|---|---|
| L1 源码剥离 | `seal.py: strip_source` | 注释、docstring、行号语义 | 字符串常量、标识符 |
| L2 字节码加密 | `app\runtime\engine.pak` | `uncompyle6` / `decompyle3` 直接读盘 | 运行期从内存 dump |
| L3 内存加载 | `stub_rt.py: _Loader/_Finder` | 磁盘上永远没有 `.pyc` | `sys.modules` 抓取（需已注入） |
| L4 签名清单 | `app\runtime\manifest.json` | 改 pak / 改页面 / 加文件 / 删文件 | 改 exe 本身（交给系统签名/哈希发布） |
| L4b 野文件扫描 | `stub_rt.py: check_tree` 尾部 | 偷放 `sitecustomize.py` / `.pth` / `.pyd` | 同签名内文件的合法替换（那就是 L4 的事） |
| L5 授权（可选） | `license.key`（机器码） | 整包拷给别人用 | 同机器复制 |
| L6 水印 | `watermark.py` | 倒卖溯源 | 刻意抹除（但会破坏 L4） |

关键点：**L2 与 L4 绑死**。pak 的密钥由 `MASTER + BUYER` 派生，manifest 覆盖
`runtime/engine.pak` 自身。所以"解密 pak 再重新打包"这条路必须先破 Ed25519，
而那需要私钥 —— 私钥不在包里（`_probe/protect/keys/priv.hex`，只留本机）。

L4b 是 L4 的补集，不是重复：清单只能证明"列出的文件没变"，对"清单之后才出现的
文件"一字不发。往 `app\runtime\` 丢一个 `sitecustomize.py`，Python 启动时自动执行它，
一个签名字节都不用碰。所以 `check_tree` 在核完哈希后再走一遍全树，
任何 `.py / .pyc / .pyd / .pth` 只要不是那三个闸门文件就拒绝。

---

## 二、怎么构建

```bat
:: 免费公开版（默认形态，不需要 license.key）
python -X utf8 _probe\protect\seal.py ^
  --buyer YG-FREE-0002 --free --wipe ^
  --app _out\AoE2ModWorkshop\app ^
  --out _cache\sealed\app

:: 拷进发布目录
rmdir /s /q _out\AoE2ModWorkshop-sealed\app
xcopy /e /i _cache\sealed\app _out\AoE2ModWorkshop-sealed\app
del _out\AoE2ModWorkshop-sealed\app\license.key

:: 门禁
python -X utf8 _probe\verify_sealed.py --app _out\AoE2ModWorkshop-sealed\app
```

产出一行：

```
seal: buyer=YG-FREE-0002 mode=free modules=91 pack=1031.3 KB boot=10.7 KB files_in_manifest=40
seal: sig ->  363URCXUT3  (trace THIS build back to a buyer)
```

### 要出"绑机器"的版本（给内测/定制买家）

```bat
python -X utf8 _probe\protect\seal.py --buyer BUYER-0042 ^
  --app _out\AoE2ModWorkshop\app --out _cache\sealed\app --wipe
python -X utf8 _probe\protect\licensing.py hwid
python -X utf8 _probe\protect\licensing.py issue --hwid <那台机器的 hwid> ^
  --buyer BUYER-0042 --days 3650 --out _cache\sealed\app\license.key
```

`--free` 缺席时闸门走授权分支：缺 `license.key` → exit 4，异机 hwid → exit 4。

⚠ **每次改 `stub_rt.py` 都要重跑 seal** —— `runtime/aoe2mod_boot.py` 是
`ed25519.py` 原文 + `stub_rt.py` 拼出来的。不重跑，跑的还是旧闸门。
`--wipe` 会删掉 `license.key`，之后必须重签。

---

## 三、启动链

```
aoe2-mod-workshop.exe
 └ engine_script() 先找 <root>\runtime\aoe2mod_launch.py   ← 封印形态优先
     └ python.exe runtime\aoe2mod_launch.py
         └ aoe2mod_boot.boot(argv)
             ├ check_license()  缺/异机 -> exit 4   （--free 时整段跳过）
             ├ check_tree()     哈希不符 / 野模块 -> exit 5
             ├ _load_pack()     解密 engine.pak 到内存
             └ import tools.run_ui -> main(argv)
```

`engine_script()` 的优先级是刻意的：先看封印入口，再看明文 `tools/run_ui.py`。
否则把 `index.html` 改坏之后，还有人能靠明文入口绕过去。

主窗口两条拒绝路径都实测过：

- 250 ms 内退出且 code ∈ {4,5} → `EngineError::Gate`，直接显示 stderr 那行；
- 250 ms 之后才退出（多数情况，要先核 40 个文件的 sha256）→ 读
  `app\protect.log` 最后一条 `拒绝启动: ...`，照样显示中文原因。

**拒绝时 `gate_refused` 会关掉内置原生引擎**。否则闸门报完错、原生兜底照跑，
两个校验都成了装饰。

---

## 四、实测结果（2026-11-14，免费版）

```
build mode                 free (no license)
no engine source on disk   ok 0 file(s)
clean boot                 ok civs=63
boots without license      ok civs=63
foreign key irrelevant     ok civs=63
refuses pack byte-flip     ok rc=5
refuses edited page        ok rc=5
buyer recorded in build    ok BUYER = 'YG-FREE-0002'
refuses stray module       ok rc=5
pack is not a .pyc         ok b'AOE2PAK1'
SEALED BUNDLE: ALL CHECKS OK
```

发布目录实测（端口 7793，sealed exe）：`/ /api/meta /api/mods /api/browse` 全 200，
`/api/meta` civs=63，日志 `real window shown`。

失败页实测文案（绑机器版、删掉 license.key）：

> 模组工坊没能启动
> [2026-11-14 19:28:33] 拒绝启动: 缺少授权文件 license.key
> 这是发布包的完整性/授权校验：文件夹被改过，或 license.key 不属于这台机器。
> 请从原始压缩包重新解压，不要修改 app\ 里的任何文件。

---

## 五、防 AI 改写

AI 拿到明文源码，最擅长的是"整体重写一遍"——哈希比对对它完全无效。所以每次构建在
**三个地方**留指纹：

1. `watermark.prepend_banner` —— 每个 `.py` 顶部一段注释，带买家码；
2. `watermark.stamp_json` —— JSON 按买家的键序序列化（内容一样，键序不同）；
3. `watermark.stamp_image_bytes` —— PNG 插 `tEXt` 块 `Comment\0aoe2mod:<sig>:<tag>`，不动像素。

`watermark.find_sig_in_tree(root)` 能扫一个疑似重打包的目录，把指纹捞回来。
AI 重写会保留值、丢掉顺序和注释 —— 正好是这三处。

---

## 六、反汇编这一侧

exe 是 Rust release 构建，`Cargo.toml` 的 `[profile.release]` 已经是：

```toml
opt-level = "s"
lto = true
codegen-units = 1
strip = true
```

`strip = true` 已经去掉符号表，`lto` + `codegen-units = 1` 把跨 crate 内联拉到最大 ——
函数边界糊在一起，反汇编出来是一大坨而不是一层层调用。再往上就是加壳（UPX /
VMProtect）：这台机器上没有，且会触发一批杀软误报，对开源免费项目不划算，不建议。

真正值钱的部分本来就不在 Python 里：`aoe2mod-serve` 与 `aoe2mod-dat` 是 Rust，
那部分从来就没法反编译回源码。

---

## 七、这层防护的真实边界

写清楚，免得高估：

- **挡不住已注入的进程**。有调试器权限或 `SetWindowsHookEx` 的人，
  `sys.modules` 里全是明文函数对象。要再抬一层只能把热路径继续挪进 Rust。
- **挡不住同机器复制**（仅指绑定版）。hwid 绑的是机器，不是人。
- **挡不住私钥泄漏**。`keys/priv.hex` 出去，整套签名失去意义 —— 那才是真正要守的东西。
- **不想用封装版的人始终有出口**。仓库里的 `tools/run_ui.py` 是明文可跑的同款引擎。
  这是刻意的：封装版的意义是让"改过包"可以被证明，不是阻止别人看见。

---

## 八、目录与中间物

| 路径 | 是什么 |
|---|---|
| `_out/AoE2ModWorkshop-sealed/` | 封印发布目录（免费版，无 license.key） |
| `_out/AoE2ModWorkshop/` | 明文发布目录，开发/同步用 |
| `_cache/sealed/app` | seal 的中间产物，拷进发布目录前先在这里验收 |
| `_probe/protect/` | seal / stub_rt / ed25519 / hwid / licensing / watermark |
| `_probe/verify_sealed.py` | 十项门禁 |
| `_probe/protect/keys/` | pub / priv / master。**私钥不进 git** |

---

## 九、待装清单（2026-11-14 决定：开发完再装）

已经装好并实测、开发期间不用再碰的：内存加载（磁盘上没有字节码）、逐文件 Ed25519 清单、
野模块扫描、水印/买家标记、免费版不绑机器。门禁是 `_probe/verify_sealed.py`，十项全绿才算完。

下面四项**明确推迟**。推迟的理由不是做不了，是它们会动到你每天看的东西：反调试会在调试时炸、
反虚拟机会在云电脑上降级、原生壳拖慢首次启动、云验证要多一个服务。开发期装它们等于给自己上绊子。

### 9.1 反汇编加固（约 20 分钟，零风险）

`Cargo.toml` 的 `[profile.release]` 已是 `strip = true` / `lto = true` /
`codegen-units = 1` / `opt-level = "s"`。再抬一档只加一行：

```toml
panic = "abort"          # 去掉 unwind 表，异常路径不再有清晰的栈
```

验收：`objdump -h` 不再出现 `.debug_*` 节；`strings` 搜不到 `aoe2mod/` 源码路径。

### 9.2 反调试（约 1 小时）

加在 `stub_rt.py` 的 `boot()` 开头、license/tree 之前 —— 先自杀再读盘：

```python
def _debugged():
    if sys.gettrace() is not None:            return True   # pdb / coverage
    if sys.getprofile() is not None:          return True
    if os.environ.get("PYTHONINSPECT"):       return True
    try:
        import ctypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if k32.IsDebuggerPresent():            return True
        ntdll = ctypes.WinDLL("ntdll")
        buf = ctypes.create_string_buffer(8)
        ntdll.NtQueryInformationProcess(       # PEB->BeingDebugged
            k32.GetCurrentProcess(), 7, buf, 8, None)
        if buf.raw[0]:                         return True
    except Exception:
        pass
    return False
```

第四层是时间差：`boot()` 首尾各记一次 `time.perf_counter()`，单步走完这段不可能超过 2 秒；
超过即当作被跟踪。**必须放在 `_load_pack` 之前**，因为解包本身要几百毫秒。

策略：**不退出，降级**。返回 `EXIT_ENGINE=6` 会让你自己也没法调试封印包，而你要调试的东西
根本不在封印包里（开发树走明文 `tools/run_ui.py`）。降级 = 只跳用水印注入和 manifest 校验。

### 9.3 反虚拟机（约 1 小时）

只在发售前的里程碑构建里开，开发期关。判定项按误报率从低到高：

1. CPUID 叶子 1 的 ECX bit 31（hypervisor present）—— 干净，但 Hyper-V/WSL2 也置位，必须配第 2 项；
2. `HKLM\SYSTEM\CurrentControlSet\Enum\IDE` 下出现 `VBOX` / `VMWARE` / `QEMU`；
3. 设备名 `\\.\VBoxGuest` / `\\.\vmci` 能否打开；
4. 进程名含 `vmtoolsd` / `VBoxService` / `qemu-ga`；
5. 系统盘序列号全 0 或全 F。

**任两项命中**才算虚拟机 —— 单项就拒绝会把 Hyper-V 上的正常玩家挡在外面。命中后同样降级不退出。

### 9.4 原生壳（半天，风险最高，最不建议）

- UPX：本机没装。`upx --best --lzma aoe2-mod-workshop.exe` 体积减 60%，但 Defender 对
  UPX 壳的启发式误报不低，开源免费项目的口碑成本大于收益。
- 自研节区加密：`main.rs` 开头加 `.text` 解密 stub，`VirtualProtect` 改 RWX 再解。
  工作量在"改完还能过 cargo build 与 tauri bundler"，不在加密本身。

判断：**不做**。Python 侧已拿掉全部可读字节码，原生侧只剩 Rust 外壳与 `aoe2mod-serve` /
`aoe2mod-dat`，那两块本来就是编译产物。壳多挡的那点东西抵不上误报和构建复杂度。

### 9.5 云端验证（一天，建议不做）

能做的：首次激活换 token、心跳、吊销名单、在线名额、远程关闸。
不做的理由：开源免费 + 离线单机工具，加云验证等于让没网的玩家开不了工；它防的"一码多机"
本来就不在这个产品的威胁模型里。

真要做，最小形态是**只做"版本公告 + 吊销名单"**：启动 `GET /v1/policy` 拿一个签名过的 JSON
（最新版号、已吊销 sig 列表），拿不到就当断网放过。既不阻碍离线使用，又能在某个买家包被
大规模倒卖时把那个 sig 拉黑。

---

### 装的时候按这个顺序

1. **9.1** —— 改两行，立刻能验，没副作用；
2. **9.2** —— 只影响封印包，开发树不受影响，先跑一遍 `verify_sealed.py` 确认十项还绿；
3. **9.3** —— 最后做，最容易误伤，要在两三台不同机器上试；
4. **9.4 / 9.5** —— 除非有具体理由，否则不做。

每装一项都要重跑 `seal.py`（`stub_rt.py` 改了 boot 就变了）再跑
`_probe/verify_sealed.py`，收尾行必须是 `SEALED BUNDLE: ALL CHECKS OK`。

