"""Benchmark cases: string."""

from __future__ import annotations

from benchmark.cases import BenchmarkCase, BenchmarkInput

KMP_CODE = """
def solve(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        return 0
    pi = [0] * len(pattern)
    j = 0
    for i in range(1, len(pattern)):
        while j and pattern[i] != pattern[j]:
            j = pi[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
    j = 0
    for i, ch in enumerate(text):
        while j and ch != pattern[j]:
            j = pi[j - 1]
        if ch == pattern[j]:
            j += 1
        if j == len(pattern):
            return i - len(pattern) + 1
    return -1
"""


KMP_TRACKER = """
def trace(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    tracer = Tracer(
        input_data,
        algorithm="KMP 字符串匹配",
        pseudocode=["构建 pi 前缀表", "匹配时用 pi[j-1] 回退 j"],
        policy="full",
        max_events=160,
    )
    pi = [0] * len(pattern)
    if pattern == "":
        tracer.create("text", state={"text": text, "pattern": pattern, "pi": pi}, reason="空模式串默认在位置 0 匹配。", code_line=1)
        tracer.result(0)
        return tracer.to_trace()
    tracer.expect_updates("pi", max(0, len(pattern) - 1))
    tracer.create("text", state={"text": text, "pattern": pattern, "pi": pi[:], "i": 0, "j": 0}, reason="展示文本串、模式串和前缀表。", code_line=1)
    j = 0
    for i in range(1, len(pattern)):
        tracer.compare(
            [f"pattern[{i}]", f"pattern[{j}]"],
            state={"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j},
            role="candidate",
            reason="构建 pi 时比较当前字符和候选前缀字符。",
            code_line=4,
        )
        while j and pattern[i] != pattern[j]:
            old_j = j
            j = pi[j - 1]
            tracer.move(
                "pointer:j",
                value=j,
                deps=[f"pi[{old_j - 1}]"],
                state={"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j},
                role="current",
                reason="构建 pi 时失配，根据已知前缀表回退 j。",
                code_line=5,
            )
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
        tracer.set(
            f"pi[{i}]",
            value=pi[i],
            deps=[f"pattern[{i}]", f"pattern[{j - 1}]"] if j else [f"pattern[{i}]"],
            state={"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j},
            role="current",
            reason="写入当前位置的最长相等真前后缀长度。",
            code_line=8,
        )
    j = 0
    result = -1
    for i, ch in enumerate(text):
        tracer.compare(
            [f"text[{i}]", f"pattern[{j}]"],
            state={"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j},
            role="candidate",
            reason="比较当前文本字符和模式字符。",
            code_line=13,
        )
        while j and ch != pattern[j]:
            old_j = j
            j = pi[j - 1]
            tracer.move(
                "pointer:j",
                value=j,
                deps=[f"pi[{old_j - 1}]"],
                state={"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j},
                role="current",
                reason="失配时根据前缀表回退模式指针。",
                code_line=15,
            )
        if ch == pattern[j]:
            j += 1
        if j == len(pattern):
            result = i - len(pattern) + 1
            tracer.mark(
                f"text[{result}:{result + len(pattern)}]",
                deps=[f"pattern[0]", f"pattern[{len(pattern) - 1}]"],
                state={"text": text, "pattern": pattern, "pi": pi[:], "i": i, "j": j, "answer": result},
                role="answer",
                reason="模式串完整匹配，返回起始位置。",
                code_line=19,
            )
            break
    if result == -1:
        tracer.explain("text", state={"text": text, "pattern": pattern, "pi": pi[:], "j": j}, reason="扫描结束，没有找到模式串。", code_line=21)
    tracer.result(result)
    return tracer.to_trace()
"""


KMP_VERIFIER = """
def verify(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        return 0
    for i in range(0, len(text) - len(pattern) + 1):
        if text[i:i + len(pattern)] == pattern:
            return i
    return -1
"""


RABIN_KARP_CODE = """
def solve(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        return 0
    m = len(pattern)
    if m > len(text):
        return -1
    base = 257
    mod = 1000000007
    high = pow(base, m - 1, mod)
    def push_hash(value):
        h = 0
        for ch in value:
            h = (h * base + ord(ch)) % mod
        return h
    pattern_hash = push_hash(pattern)
    window_hash = push_hash(text[:m])
    for i in range(0, len(text) - m + 1):
        if window_hash == pattern_hash and text[i:i + m] == pattern:
            return i
        if i < len(text) - m:
            window_hash = ((window_hash - ord(text[i]) * high) * base + ord(text[i + m])) % mod
    return -1
"""


RABIN_KARP_TRACKER = """
def trace(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    tracer = Tracer(
        input_data,
        algorithm="Rabin-Karp 滚动哈希",
        pseudocode=["计算 pattern_hash", "滚动维护每个 text 窗口哈希", "哈希命中后逐字符确认"],
        policy="full",
        max_events=160,
    )
    base = 257
    mod = 1000000007
    def push_hash(value):
        h = 0
        for ch in value:
            h = (h * base + ord(ch)) % mod
        return h
    pattern_hash = push_hash(pattern)
    m = len(pattern)
    window_count = max(0, len(text) - m + 1) if m else 0
    window_hashes = [None] * window_count
    tracer.create(
        "text",
        state={"text": text, "pattern": pattern, "pattern_hash": pattern_hash, "window_hashes": window_hashes[:]},
        reason="展示文本串、模式串和 pattern_hash，准备滚动哈希窗口。",
        code_line=1,
    )
    if pattern == "":
        tracer.result(0)
        return tracer.to_trace()
    if m > len(text):
        tracer.explain(
            "text",
            state={"text": text, "pattern": pattern, "pattern_hash": pattern_hash, "window_hashes": window_hashes[:]},
            reason="模式串长于文本串，Rabin-Karp 无可比较窗口。",
            code_line=2,
        )
        tracer.result(-1)
        return tracer.to_trace()
    first_match = -1
    for start in range(window_count):
        if text[start:start + m] == pattern:
            first_match = start
            break
    scanned_windows = window_count if first_match == -1 else first_match + 1
    tracer.expect_updates("window_hashes", scanned_windows)
    high = pow(base, m - 1, mod)
    window_hash = 0
    result = -1
    for i in range(window_count):
        if i == 0:
            window_hash = push_hash(text[:m])
            deps = [f"text[0:{m}]"]
            reason = "计算第一个窗口的 Rabin-Karp 哈希。"
        else:
            window_hash = ((window_hash - ord(text[i - 1]) * high) * base + ord(text[i + m - 1])) % mod
            deps = [f"window_hashes[{i - 1}]", f"text[{i - 1}]", f"text[{i + m - 1}]"]
            reason = "用移出字符和移入字符滚动哈希，得到下一个窗口哈希。"
        window_hashes[i] = window_hash
        tracer.set(
            f"window_hashes[{i}]",
            value=window_hash,
            deps=deps,
            state={"text": text, "pattern": pattern, "pattern_hash": pattern_hash, "window_hashes": window_hashes[:], "window_start": i, "window_hash": window_hash},
            role="current",
            reason=reason,
            code_line=8,
        )
        tracer.compare(
            [f"text[{i}:{i + m}]", "pattern"],
            deps=[f"window_hashes[{i}]", "pattern_hash"],
            value={"window_hash": window_hash, "pattern_hash": pattern_hash},
            state={"text": text, "pattern": pattern, "pattern_hash": pattern_hash, "window_hashes": window_hashes[:], "window_start": i, "window_hash": window_hash},
            role="candidate",
            reason="比较窗口哈希和 pattern_hash；哈希相等时再确认字符，避免碰撞误判。",
            code_line=10,
        )
        if window_hash == pattern_hash and text[i:i + m] == pattern:
            result = i
            tracer.mark(
                f"text[{i}:{i + m}]",
                deps=["pattern", f"window_hashes[{i}]"],
                state={"text": text, "pattern": pattern, "pattern_hash": pattern_hash, "window_hashes": window_hashes[:], "window_start": i, "answer": result},
                role="answer",
                reason="窗口哈希与模式哈希相等，逐字符确认后返回匹配起点。",
                code_line=11,
            )
            break
    if result == -1:
        tracer.explain(
            "text",
            state={"text": text, "pattern": pattern, "pattern_hash": pattern_hash, "window_hashes": window_hashes[:]},
            reason="所有窗口的滚动哈希都未确认匹配。",
            code_line=13,
        )
    tracer.result(result)
    return tracer.to_trace()
"""


RABIN_KARP_VERIFIER = """
def verify(input_data):
    text = input_data["text"]
    pattern = input_data["pattern"]
    if pattern == "":
        return 0
    for i in range(0, len(text) - len(pattern) + 1):
        if text[i:i + len(pattern)] == pattern:
            return i
    return -1
"""


Z_ALGORITHM_CODE = """
def solve(input_data):
    text = input_data["text"]
    n = len(text)
    z = [0] * n
    left = 0
    right = 0
    for i in range(1, n):
        if i <= right:
            z[i] = min(right - i + 1, z[i - left])
        while i + z[i] < n and text[z[i]] == text[i + z[i]]:
            z[i] += 1
        if i + z[i] - 1 > right:
            left = i
            right = i + z[i] - 1
    return z
"""


Z_ALGORITHM_TRACKER = """
def trace(input_data):
    text = input_data["text"]
    n = len(text)
    tracer = Tracer(
        input_data,
        algorithm="Z Algorithm 字符串前缀匹配",
        pseudocode=["z[i] 表示 text[i:] 与 text 的最长公共前缀长度", "维护当前 Z-box [l,r]", "必要时向右扩展"],
        policy="full",
        max_events=180,
    )
    z = [0] * n
    left = 0
    right = 0
    tracer.expect_updates("z", max(0, n - 1))
    tracer.create("text", state={"text": text, "z": z[:], "l": left, "r": right}, reason="展示字符串和 Z 数组，初始化空 Z-box。", code_line=1)
    for i in range(1, n):
        if i <= right:
            z[i] = min(right - i + 1, z[i - left])
            tracer.compare(
                [f"z[{i}]", f"z[{i - left}]"],
                state={"text": text, "z": z[:], "l": left, "r": right, "i": i},
                role="candidate",
                reason="i 落在当前 Z-box 内，先复用镜像位置的 Z 值作为下界。",
                code_line=5,
            )
        while i + z[i] < n and text[z[i]] == text[i + z[i]]:
            tracer.compare(
                [f"text[{z[i]}]", f"text[{i + z[i]}]"],
                state={"text": text, "z": z[:], "l": left, "r": right, "i": i},
                role="candidate",
                reason="Z Algorithm 继续比较前缀字符和当前位置后续字符，尝试扩展 Z-box。",
                code_line=7,
            )
            z[i] += 1
        if i + z[i] - 1 > right:
            left = i
            right = i + z[i] - 1
        deps = [f"text[0:{z[i]}]", f"text[{i}:{i + z[i]}]"] if z[i] else [f"text[{i}]"]
        tracer.set(
            f"z[{i}]",
            value=z[i],
            deps=deps,
            state={"text": text, "z": z[:], "l": left, "r": right, "i": i},
            role="current",
            reason="写入当前位置的 Z 值，并同步当前 Z-box 边界。",
            code_line=10,
        )
    tracer.result(z)
    return tracer.to_trace()
"""


Z_ALGORITHM_VERIFIER = """
def verify(input_data):
    text = input_data["text"]
    z = [0] * len(text)
    for i in range(1, len(text)):
        while i + z[i] < len(text) and text[z[i]] == text[i + z[i]]:
            z[i] += 1
    return z
"""


MANACHER_CODE = """
def solve(input_data):
    text = input_data["text"]
    transformed = "#" + "#".join(text) + "#"
    radius = [0] * len(transformed)
    center = 0
    right = 0
    for i in range(len(transformed)):
        mirror = 2 * center - i
        if i < right and 0 <= mirror < len(transformed):
            radius[i] = min(right - i, radius[mirror])
        while i - radius[i] - 1 >= 0 and i + radius[i] + 1 < len(transformed) and transformed[i - radius[i] - 1] == transformed[i + radius[i] + 1]:
            radius[i] += 1
        if i + radius[i] > right:
            center = i
            right = i + radius[i]
    return max(radius) if radius else 0
"""


MANACHER_TRACKER = """
def trace(input_data):
    raw_text = input_data["text"]
    text = "#" + "#".join(raw_text) + "#"
    radius = [0] * len(text)
    center = 0
    right = 0
    tracer = Tracer(
        input_data,
        algorithm="Manacher 回文半径",
        pseudocode=["给原字符串插入分隔符", "使用 mirror 半径初始化", "向两侧扩展并维护最右回文边界"],
        policy="full",
        max_events=220,
    )
    tracer.expect_updates("radius", len(text))
    tracer.create(
        "text",
        state={"text": text, "raw_text": raw_text, "radius": radius[:], "center": center, "right": right},
        reason="插入分隔符后展示统一奇偶回文模型和 radius 数组。",
        code_line=1,
    )
    for i in range(len(text)):
        mirror = 2 * center - i
        if i < right and 0 <= mirror < len(text):
            radius[i] = min(right - i, radius[mirror])
            tracer.compare(
                [f"radius[{i}]", f"radius[{mirror}]"],
                state={"text": text, "raw_text": raw_text, "radius": radius[:], "center": center, "right": right, "i": i, "mirror": mirror},
                role="candidate",
                reason="当前位置在最右回文覆盖内，先用 mirror 位置的回文半径作为初始值。",
                code_line=7,
            )
        while i - radius[i] - 1 >= 0 and i + radius[i] + 1 < len(text) and text[i - radius[i] - 1] == text[i + radius[i] + 1]:
            tracer.compare(
                [f"text[{i - radius[i] - 1}]", f"text[{i + radius[i] + 1}]"],
                state={"text": text, "raw_text": raw_text, "radius": radius[:], "center": center, "right": right, "i": i},
                role="candidate",
                reason="Manacher 从当前中心向两侧做半径扩展。",
                code_line=9,
            )
            radius[i] += 1
        if i + radius[i] > right:
            center = i
            right = i + radius[i]
        left_dep = max(0, i - radius[i])
        right_dep = min(len(text) - 1, i + radius[i])
        tracer.set(
            f"radius[{i}]",
            value=radius[i],
            deps=[f"text[{left_dep}]", f"text[{right_dep}]"],
            state={"text": text, "raw_text": raw_text, "radius": radius[:], "center": center, "right": right, "i": i},
            role="current",
            reason="写入当前中心的回文半径，并更新最右回文边界。",
            code_line=12,
        )
    answer = max(radius) if radius else 0
    best_center = radius.index(answer) if radius else 0
    tracer.mark(
        f"radius[{best_center}]",
        value=answer,
        state={"text": text, "raw_text": raw_text, "radius": radius[:], "center": best_center, "right": best_center + answer, "answer": answer},
        role="answer",
        reason="最大回文半径就是原字符串中的最长回文子串长度。",
        code_line=15,
    )
    tracer.result(answer)
    return tracer.to_trace()
"""


MANACHER_VERIFIER = """
def verify(input_data):
    text = input_data["text"]
    best = 0
    for i in range(len(text)):
        for j in range(i, len(text)):
            piece = text[i:j + 1]
            if piece == piece[::-1] and len(piece) > best:
                best = len(piece)
    return best
"""


STRING_SLIDING_WINDOW_UNIQUE_CODE = """
def solve(input_data):
    text = input_data["text"]
    last = {}
    left = 0
    best = 0
    for right, ch in enumerate(text):
        if ch in last and last[ch] >= left:
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best
"""


STRING_SLIDING_WINDOW_UNIQUE_TRACKER = """
def trace(input_data):
    text = input_data["text"]
    pattern = ""
    contract = {
        "family": "string",
        "submode": "string_sliding_window",
        "expected_tables": ["window_counts"],
        "expected_events": ["move_pointer"] if text else [],
    }
    tracer = Tracer(
        input_data,
        algorithm="字符串滑动窗口最长无重复子串",
        pseudocode=["右端逐字符扩张窗口", "遇到重复字符时移动左端", "维护无重复窗口的最长长度"],
        policy="full",
        max_events=180,
    )
    tracer.expect_updates("pointer:right", len(text))
    last = {}
    counts = {}
    left = 0
    best = 0
    tracer.create(
        "text" if text else "text[0:0]",
        state={"text": text, "pattern": pattern, "i": 0, "j": 0, "left": 0, "right": -1, "window_counts": dict(counts), "best": best, "family_contract": contract},
        reason="初始化字符串滑动窗口，窗口内保持字符不重复。",
        code_line=1,
    )
    for right, ch in enumerate(text):
        will_shrink = ch in last and last[ch] >= left
        counts[ch] = counts.get(ch, 0) + 1
        right_reason = "右端纳入当前字符后检测到重复，下一步收缩左端。" if will_shrink else "右端纳入当前字符。"
        tracer.move(
            "pointer:right",
            value=right,
            deps=[f"text[{right}]"],
            state={"text": text, "pattern": pattern, "i": right, "j": 0, "left": left, "right": right, "window_counts": dict(counts), "best": best, "window_reason": right_reason, "family_contract": contract},
            role="current",
            reason=right_reason,
            code_line=6,
        )
        if will_shrink:
            old_left = left
            while left <= last[ch]:
                out = text[left]
                counts[out] -= 1
                if counts[out] == 0:
                    del counts[out]
                left += 1
                tracer.move(
                    "pointer:left",
                    value=left,
                    deps=[f"text[{left - 1}]", f"text[{right}]"],
                    state={"text": text, "pattern": pattern, "i": right, "j": 0, "left": left, "right": right, "window_counts": dict(counts), "best": best, "window_reason": "重复字符触发左端收缩。", "family_contract": contract},
                    role="current",
                    reason="窗口内出现重复字符，移动左端直到重复字符被移出。",
                    code_line=8,
                )
            if old_left == left:
                tracer.explain(
                    "text",
                    state={"text": text, "pattern": pattern, "i": right, "j": 0, "left": left, "right": right, "window_counts": dict(counts), "best": best, "family_contract": contract},
                    reason="重复字符位置已经在当前窗口左侧，不需要收缩。",
                    code_line=8,
                )
        last[ch] = right
        best = max(best, right - left + 1)
        tracer.mark(
            f"text[{left}:{right + 1}]",
            value=best,
            deps=[f"text[{right}]"],
            state={"text": text, "pattern": pattern, "i": right, "j": 0, "left": left, "right": right, "window_counts": dict(counts), "best": best, "family_contract": contract},
            role="candidate",
            reason="当前窗口无重复，更新最长长度候选。",
            code_line=12,
        )
    answer_target = f"text[{left}:{len(text)}]" if text else "text[0:0]"
    tracer.mark(
        answer_target,
        value=best,
        state={"text": text, "pattern": pattern, "i": max(0, len(text) - 1), "j": 0, "left": left, "right": len(text) - 1, "window_counts": dict(counts), "best": best, "answer": best, "family_contract": contract},
        role="answer",
        reason="扫描结束，最长无重复子串长度就是答案。",
        code_line=13,
    )
    tracer.result(best)
    return tracer.to_trace()
"""


STRING_SLIDING_WINDOW_UNIQUE_VERIFIER = """
def verify(input_data):
    text = input_data["text"]
    best = 0
    for i in range(len(text)):
        seen = set()
        for j in range(i, len(text)):
            if text[j] in seen:
                break
            seen.add(text[j])
            best = max(best, j - i + 1)
    return best
"""


TRIE_PREFIX_MATCH_STRING_CODE = """
def solve(input_data):
    words = input_data["words"]
    prefix = input_data["prefix"]
    return sum(1 for word in words if word.startswith(prefix))
"""


TRIE_PREFIX_MATCH_STRING_TRACKER = """
def trace(input_data):
    words = input_data["words"]
    prefix = input_data["prefix"]
    contract = {"family": "string", "submode": "trie_prefix_match", "expected_tables": ["prefix_count"], "expected_events": ["compare"]}
    trie = {"nodes": [{"id": "root", "label": "root", "meta": {"count": 0}}], "edges": []}
    children = {"root": {}}
    node_meta = {"root": {"count": 0}}
    tracer = Tracer(
        input_data,
        algorithm="Trie 前缀匹配字符串路径",
        pseudocode=["插入 words 时更新经过节点的 prefix_count", "沿 prefix 的字符路径前进", "路径结束节点的 count 即匹配数量"],
        policy="full",
        max_events=220,
    )
    tracer.create(
        "trie",
        state={"text": prefix, "pattern": prefix, "i": 0, "j": 0, "words": words, "prefix": prefix, "trie": trie, "prefix_count": 0, "family_contract": contract},
        reason="初始化 Trie 根节点，准备插入单词并复核前缀字符路径。",
        code_line=1,
    )
    for word_index, word in enumerate(words):
        cur = "root"
        node_meta[cur]["count"] += 1
        trie["nodes"][0]["meta"]["count"] = node_meta[cur]["count"]
        for char_index, ch in enumerate(word):
            if ch not in children[cur]:
                nxt = f"{cur}_{ch}_{len(trie['nodes'])}"
                children[cur][ch] = nxt
                children[nxt] = {}
                node_meta[nxt] = {"count": 0, "terminal": False}
                trie["nodes"].append({"id": nxt, "label": ch, "meta": dict(node_meta[nxt])})
                trie["edges"].append([cur, nxt])
                tracer.link(
                    f"node:{nxt}",
                    deps=[f"node:{cur}", f"words[{word_index}]"],
                    state={"text": prefix, "pattern": prefix, "i": char_index, "j": char_index, "words": words, "prefix": prefix, "trie": {"nodes": [dict(node) for node in trie["nodes"]], "edges": trie["edges"][:]}, "char": ch, "prefix_count": 0, "family_contract": contract},
                    role="current",
                    reason="插入单词时按字符创建 Trie 节点。",
                    code_line=9,
                )
            cur = children[cur][ch]
            node_meta[cur]["count"] += 1
            if char_index == len(word) - 1:
                node_meta[cur]["terminal"] = True
            for node in trie["nodes"]:
                if node["id"] == cur:
                    node["meta"] = dict(node_meta[cur])
                    break
    cur = "root"
    count = 0
    for index, ch in enumerate(prefix):
        tracer.compare(
            [f"text[{index}]", f"node:{cur}"],
            deps=[f"text[{index}]", f"node:{cur}"],
            state={"text": prefix, "pattern": prefix, "i": index, "j": index, "words": words, "prefix": prefix, "trie": {"nodes": [dict(node) for node in trie["nodes"]], "edges": trie["edges"][:]}, "current": cur, "char": ch, "prefix_count": count, "family_contract": contract},
            role="candidate",
            reason="按前缀当前字符沿 Trie 边向下匹配。",
            code_line=15,
        )
        if ch not in children.get(cur, {}):
            cur = ""
            count = 0
            break
        cur = children[cur][ch]
        count = node_meta[cur]["count"]
        tracer.mark(
            f"node:{cur}",
            value=count,
            deps=[f"text[{index}]", f"node:{cur}"],
            state={"text": prefix, "pattern": prefix, "i": index, "j": index, "words": words, "prefix": prefix, "trie": {"nodes": [dict(node) for node in trie["nodes"]], "edges": trie["edges"][:]}, "current": cur, "char": ch, "prefix_count": count, "family_contract": contract},
            role="current",
            reason="前缀字符匹配成功，当前节点 count 表示经过该节点的单词数。",
            code_line=19,
        )
    answer = len(words) if prefix == "" else count
    target = f"node:{cur}" if cur else "trie"
    tracer.mark(
        target,
        value=answer,
        deps=[target] if cur else ["trie"],
        state={"text": prefix, "pattern": prefix, "i": max(0, len(prefix) - 1), "j": max(0, len(prefix) - 1), "words": words, "prefix": prefix, "trie": {"nodes": [dict(node) for node in trie["nodes"]], "edges": trie["edges"][:]}, "current": cur or "missing", "prefix_count": answer, "answer": answer, "family_contract": contract},
        role="answer",
        reason="前缀路径结束，当前节点 prefix_count 就是匹配单词数量。",
        code_line=22,
    )
    tracer.result(answer)
    return tracer.to_trace()
"""


TRIE_PREFIX_MATCH_STRING_VERIFIER = """
def verify(input_data):
    return sum(1 for word in input_data["words"] if word.startswith(input_data["prefix"]))
"""


def cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase(
            id="kmp",
            title="KMP 字符串匹配",
            problem=(
                "实现字符串匹配。给定 text 和 pattern，返回 pattern 在 text 中第一次出现的起始下标；"
                "如果不存在返回 -1；如果 pattern 为空返回 0。希望使用 KMP 或等价的线性字符串匹配思路。"
            ),
            family="字符串高级算法",
            input_contract="输入 text 和 pattern。",
            variant_name="前缀表匹配",
            strategy="使用 KMP 前缀表，trace 只记录初始化、一次前缀表更新、一次失配回退、一次成功匹配等关键步骤，不要逐字符展开全部循环。",
            time_complexity="O(n+m)",
            space_complexity="O(m)",
            expected_layouts=("string",),
            code=KMP_CODE,
            tracker_code=KMP_TRACKER,
            verifier_code=KMP_VERIFIER,
            samples=(
                BenchmarkInput({"text": "ababc", "pattern": "abc"}, 2),
                BenchmarkInput({"text": "aaaaa", "pattern": "bba"}, -1),
                BenchmarkInput({"text": "abc", "pattern": ""}, 0),
            ),
        ),
        BenchmarkCase(
            id="rabin_karp",
            title="Rabin-Karp 字符串匹配",
            problem=(
                "给定 text 和 pattern，返回 pattern 在 text 中第一次出现的起始下标；"
                "使用 Rabin-Karp 滚动哈希比较每个等长窗口，哈希命中后再逐字符确认。"
            ),
            family="字符串高级算法",
            input_contract="输入 text 和 pattern。",
            variant_name="滚动哈希匹配",
            strategy="计算 pattern_hash，滚动维护 text 窗口哈希，哈希相等时确认字符。",
            time_complexity="O(n+m)",
            space_complexity="O(n)",
            expected_layouts=("string",),
            code=RABIN_KARP_CODE,
            tracker_code=RABIN_KARP_TRACKER,
            verifier_code=RABIN_KARP_VERIFIER,
            samples=(
                BenchmarkInput({"text": "abcdef", "pattern": "cde"}, 2),
                BenchmarkInput({"text": "aaaaa", "pattern": "aa"}, 0),
                BenchmarkInput({"text": "abc", "pattern": "abcd"}, -1),
            ),
        ),
        BenchmarkCase(
            id="z_algorithm",
            title="Z Algorithm 前缀匹配表",
            problem=(
                "给定字符串 text，返回 Z 数组。z[i] 表示 text[i:] 与 text 的最长公共前缀长度。"
                "过程需要展示 Z-box 复用和向右扩展。"
            ),
            family="字符串高级算法",
            input_contract="输入 text 字符串。",
            variant_name="Z-box 线性扫描",
            strategy="维护当前 Z-box [l,r]，在盒内复用镜像值，并继续比较扩展。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("string",),
            code=Z_ALGORITHM_CODE,
            tracker_code=Z_ALGORITHM_TRACKER,
            verifier_code=Z_ALGORITHM_VERIFIER,
            samples=(
                BenchmarkInput({"text": "aabcaabx"}, [0, 1, 0, 0, 3, 1, 0, 0]),
                BenchmarkInput({"text": "aaaaa"}, [0, 4, 3, 2, 1]),
                BenchmarkInput({"text": "abc"}, [0, 0, 0]),
            ),
        ),
        BenchmarkCase(
            id="manacher",
            title="Manacher 最长回文子串长度",
            problem=(
                "给定字符串 text，返回最长回文子串长度。"
                "使用 Manacher 算法在插入分隔符后的字符串上维护每个中心的回文半径。"
            ),
            family="字符串高级算法",
            input_contract="输入 text 字符串。",
            variant_name="回文半径扩展",
            strategy="插入分隔符统一奇偶长度，使用 mirror 半径初始化并向两侧扩展。",
            time_complexity="O(n)",
            space_complexity="O(n)",
            expected_layouts=("string",),
            code=MANACHER_CODE,
            tracker_code=MANACHER_TRACKER,
            verifier_code=MANACHER_VERIFIER,
            samples=(
                BenchmarkInput({"text": "ababa"}, 5),
                BenchmarkInput({"text": "cbbd"}, 2),
                BenchmarkInput({"text": "abc"}, 1),
            ),
        ),
        BenchmarkCase(
            id="string_sliding_window_unique",
            title="字符串滑动窗口最长无重复子串",
            problem="给定字符串 text，返回不含重复字符的最长子串长度；过程需要展示窗口左右端和字符计数。",
            family="字符串高级算法",
            input_contract="输入 text 字符串。",
            variant_name="无重复滑动窗口",
            strategy="右端逐字符扩张窗口，遇到重复字符时移动左端并维护 window_counts。",
            time_complexity="O(n)",
            space_complexity="O(字符集大小)",
            expected_layouts=("string", "map"),
            code=STRING_SLIDING_WINDOW_UNIQUE_CODE,
            tracker_code=STRING_SLIDING_WINDOW_UNIQUE_TRACKER,
            verifier_code=STRING_SLIDING_WINDOW_UNIQUE_VERIFIER,
            samples=(
                BenchmarkInput({"text": "abcabcbb"}, 3),
                BenchmarkInput({"text": "bbbbb"}, 1),
                BenchmarkInput({"text": ""}, 0),
            ),
        ),
        BenchmarkCase(
            id="trie_prefix_match_string",
            title="Trie 前缀匹配字符串路径",
            problem="给定字符串数组 words 和前缀 prefix，沿 Trie 的字符路径统计以 prefix 开头的单词数量。",
            family="字符串高级算法",
            input_contract="输入 words 和 prefix。",
            variant_name="Trie 前缀路径匹配",
            strategy="构建 Trie 并在每个节点维护 prefix_count，再沿 prefix 字符路径读取计数。",
            time_complexity="O(总字符数)",
            space_complexity="O(总字符数)",
            expected_layouts=("trie", "string"),
            code=TRIE_PREFIX_MATCH_STRING_CODE,
            tracker_code=TRIE_PREFIX_MATCH_STRING_TRACKER,
            verifier_code=TRIE_PREFIX_MATCH_STRING_VERIFIER,
            samples=(
                BenchmarkInput({"words": ["apple", "app", "ape", "bat"], "prefix": "ap"}, 3),
                BenchmarkInput({"words": ["dog", "door", "deer"], "prefix": "doo"}, 1),
                BenchmarkInput({"words": ["cat", "car"], "prefix": "z"}, 0),
            ),
        ),
    )
