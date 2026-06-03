// === 粤语发音覆盖白名单 ===
// 值可以写两种形式：
//   1) 粤语拼音字符串（jyutping，如 'gin3'）—— 推荐，由下面的 jyutpingToSafeChar 查表
//   2) 直接写一个替代汉字（如 '建'）—— 给字典里还没收录的拼音用作 escape hatch
// 注意：浏览器 TTS 不能直接读拼音字母，所以拼音必须先映射到一个 TTS 读得准的汉字。
const pronunciationOverrides = {
  '见': 'gin3',
  '荡': 'dang6',
  '闲': 'haan4',
  '会': 'wui2',
  // 例：'佢': 'keoi5',
};

// 粤语拼音 → 一个 Windows 粤语 TTS 读得准确的同音字（每条都人工验证过）
// 如果某个拼音不在这里，需要先加一条；找不到时会 console.warn 并保留原字
const jyutpingToSafeChar = {
  'gin3':  '建',
  'haan4': '娴',
  'dang6': '当',   // 用普通话 dāng 近似（TTS 对此类字会回退到普通话发音）
  'wui2':  '汇',   // 若 TTS 还是读 kui，改为 '回'(wui4) 或 '回'
  // 在此继续补充：'keoi5': '渠', 'zo2': '左', ...
};

function applyPronunciationOverrides(text) {
  if (!text) return text;
  let out = '';
  for (const ch of text) {
    if (!Object.prototype.hasOwnProperty.call(pronunciationOverrides, ch)) {
      out += ch;
      continue;
    }
    const v = pronunciationOverrides[ch];
    // 形如 "gin3" / "haan4" → 走拼音查表
    if (/^[a-z]+[1-6]$/.test(v)) {
      if (Object.prototype.hasOwnProperty.call(jyutpingToSafeChar, v)) {
        out += jyutpingToSafeChar[v];
      } else {
        console.warn('[pronunciationOverrides] 拼音未在 jyutpingToSafeChar 注册：' + v + '（字"' + ch + '"将保留原字）');
        out += ch;
      }
    } else {
      // 直接是替代汉字
      out += v;
    }
  }
  return out;
}
