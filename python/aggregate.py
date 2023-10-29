#!python3.10
# coding: shift_jis

import sys
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from distutils.util import strtobool

#================
# 定数
#================
# SMFの最大トラック数
SMF_TRACK_MAXCOUNT = 16

# SMFにおいて半音に対応するピッチベンド値
SMF_HALFTONE_PBVALUE = 8192

# 周波数
LOWEST_FREQ = 8.1758
HALFTONE_FREQ_COEFF = 2 ** (1/12)


#================
# 関数
#================
# パンの数値からパンの種類を判別
def getPanClassification(_pan):
    if (_pan == 64):
        return 0 #C
    elif (_pan == 127):
        return 2 #R端
    elif (_pan == 0):
        return -2 #L端
    elif(_pan > 64):
        return 1 #R
    else:
        return -1 #L

# 分析した正味曲数を取得
def getanalyzedFilesCount(_logFilePath: str):
    logs = ""
    with open(_logFilePath, mode="rb") as f:
        logs = f.read().split(b"\x0D\x00\x0A\x00")
    allFilesCount = 0
    analyzedFilesCount = 0
    for log in logs:
        allFilesCount += 1
        if (log[:10] == b"\x46\x00\x69\x00\x6C\x00\x65\x00\x3A\x00"):
            analyzedFilesCount += 1
    print(f"FileCount: {analyzedFilesCount} / {allFilesCount}")
    return analyzedFilesCount

# 度数分布を作成
def FreqDist(_data, _classWidth=None, _isInt=True, _dataMin=None, _dataMax=None):
    dataNp = _data.to_numpy()
    classWidth = 0
    if (_classWidth is None):
        class_size = int(np.log2(dataNp.size).round()) + 1
        if (_isInt):
            classWidth = round((dataNp.max() - dataNp.min()) / class_size)
        else:
            classWidth = (dataNp.max() - dataNp.min()) / class_size
    else:
        classWidth = _classWidth
    

    dataMin = _dataMin
    if (dataMin is None):
        dataMin = dataNp.min()
    dataMax = _dataMax
    if (dataMax is None):
        dataMax = dataNp.max()
    dataMax += 1.5*classWidth
    bins = np.arange(dataMin, dataMax, classWidth)


    print(dataMin, dataMax, classWidth)

    hist = np.histogram(dataNp, bins)[0]
    cumSum = hist.cumsum()

    return pd.DataFrame({"階級値": (bins[1:] + bins[:-1]) / 2,
                         "度数": hist,
                         "累積度数": cumSum,
                         "相対度数": hist / cumSum[-1],
                         "累積相対度数": cumSum / cumSum[-1]},
                        index=pd.Index([f"{bins[i]}以上{bins[i+1]}未満"
                                        for i in range(hist.size)],
                                       name="階級"))

# 統計情報をまとめて出力
def outputStat(_statCols, _res: pd.DataFrame, _figFileBase: str):
    for c in _statCols:
        # 要約
        s_res = _res[c]
        # 平均値
        s_mean = s_res.mean()
        # 標準偏差
        s_sigma = s_res.std(ddof=0)
        # 中央値
        s_median = s_res.median()
        # 最大値・最小値
        s_maxdata = s_res.max()
        s_mindata = s_res.min()
        # 最頻値
        s_mode = s_res.mode()
        # 度数分布
        # 階級幅
        s_classWidth = 1
        if ((c == "X_ovVol") or (c == "Y_ovVol") or (c == "Diff_ovVol")):
            s_classWidth = 0.1
        elif (c == "Diff_timing(Beats)"):
            s_classWidth = 0.125
        elif ((c == "X_pitch") or (c == "Y_pitch") or (c == "Diff_pitch")):
            s_classWidth = 256
        elif (c == "Diff_timing(MicroSeconds)"):
            s_classWidth = 10000
        elif ((c == "X_pitchFreq") or (c == "Y_pitchFreq") or (c == "Diff_freq")):
            s_classWidth = 5
        # 整数かどうか
        s_isInt = True
        if ((c == "X_ovVol") or (c == "X_pitchFreq")
            or (c == "Y_ovVol") or (c == "Y_pitchFreq")
            or (c == "Diff_timing(MicroSeconds)") or (c == "Diff_ovVol")):
            s_isInt = False
        # 最小値
        s_min = -0.5
        if ((c == "X_pitch") or (c == "X_ovVol") 
            or (c == "Y_pitch") or (c == "Y_ovVol")
            or (c == "Diff_pitch") or (c == "Diff_ovVol") or (c== "Diff_octave")):
            s_min = None
        elif ((c == "Diff_timing(MicroSeconds)") or (c == "Diff_timing(Beats)")):
            s_min = 0
        elif ((c == "Diff_pan")
              or (c == "Diff_velocity") or (c == "Diff_expression") or (c == "Diff_mainVol")):
            s_min = -127.5
        elif ((c == "X_panClassification") or (c == "Y_panClassification")):
            s_min = -2.5
        elif ((c == "X_pitchFreq") or (c == "Y_pitchFreq")):
            s_min = -360
        elif ((c == "Diff_freq")):
            s_min = -260
        # 最大値
        s_max = 1
        if ((c == "X_pan") or (c == "Y_pan")
            or (c == "X_velocity") or (c == "Y_velocity")
            or (c == "X_expression") or (c == "Y_expression")
            or (c == "X_mainVol") or (c == "Y_mainVol")
            or (c == "Diff_pan")
            or (c == "Diff_velocity") or (c == "Diff_expression") or (c == "Diff_mainVol")):
            s_max = 127
        elif ((c == "X_pitch") or (c == "X_ovVol") 
              or (c == "Y_pitch") or (c == "Y_ovVol")
              or (c == "Diff_timing(MicroSeconds)")
              or (c == "Diff_pitch") or (c == "Diff_ovVol") or (c == "Diff_octave")):
            s_max = None
        elif ((c == "Diff_program(group)") or (c == "X_panClassification") or (c == "Y_panClassification")):
            s_max = 2
        elif ((c == "X_pitchFreq") or (c == "Y_pitchFreq")):
            s_max = 360
        elif ((c == "Diff_freq")):
            s_max = 260

        # グラフ作成
        # テキストデータ
        s_labelText = f"平均値:{s_mean:.3f}\n標準偏差:{s_sigma:.3f}\n中央値:{s_median:.3f}\n"
        s_labelText += f"最大値{s_maxdata:.3f}:\n最小値:{s_mindata:.3f}\n"
        s_vc = s_res.value_counts(normalize=True)
        if (c == "Diff_timing(Beats)"):
            s_vc.to_csv(f"result/{_figFileBase}{c}_value_counts.csv")
        for m in s_mode:
            s_labelText += f"最頻値:{m:.3f}, 相対頻度:{s_vc.loc[m]:.3f}\n"
        if (s_classWidth is not None):
            s_labelText += f"階級幅:{s_classWidth:.3f}"
        # グラフ本体
        s_fd = FreqDist(s_res, s_classWidth, s_isInt, s_min, s_max)
        s_fig, s_ax = plt.subplots(nrows=1, ncols=1, figsize=(max(round(len(s_fd)*1.2), 20), 20))

        p = s_ax.bar(x=s_fd["階級値"], height=s_fd["相対度数"], ec="k", lw=1,
                    width=s_classWidth,
                    label=s_labelText)
        s_ax.bar_label(p, fmt="%.3f", fontsize=10)
        s_ax.set_xticks(s_fd["階級値"])
        s_ax.set_title(c)
        s_ax.legend(fontsize=16)

        # 図保存
        s_fig.savefig(f"result/{_figFileBase}{c}.png", bbox_inches="tight")
        # print(f"saved: {_figFileBase}{c}.png")


# 相関比
def CorrelationV(x, y):
    variation = ((y - y.mean()) ** 2).sum()
    interClass = sum([((y[x == i] - y[x == i].mean()) ** 2).sum() for i in np.unique(x)])
    corrRatio = interClass / variation
    return 1 - corrRatio

# ================
# メイン処理
# ================
logFilePath = "exlog.txt"
resultFilePath = "out.csv"

# 分析した正味曲数を取得
analyzedFilesCount = getanalyzedFilesCount(logFilePath)

# 分析結果からデータフレーム作成
res = pd.read_csv(resultFilePath, header=0, sep=';',
                  dtype={"File":"str", "Base":"str", "IsStrong":"bool"})
print(res.columns)

# columns: ['File', 'TicksPerBeat', 'TrackX', 'TrackY', 'IsStrong', 'Section',
#    'SectionLength(Bar)', 'Score', 'MsgNumber', 'GlobalTick', 'NoteNumber',
#    'Base', 
#    'X_tempo', 'X_program', 'X_pitch', 'X_pan', 'X_ovVol',
#    'Y_tempo', 'Y_program', 'Y_pitch', 'Y_pan', 'Y_ovVol', 
#    'Diff_timing',
#    'Diff_timing(MicroSeconds)', 'Diff_program', 'Diff_program(group)',
#    'Diff_pitch', 'Diff_pan', 'Diff_ovVol', 'Diff_octave']

# ディレイの実時間（マイクロ秒単位）を求める
# 実時間 = ティック単位の時間 * テンポ(四分音符あたりのマイクロ秒数) / 分解能(四分音符あたりのティック数)
res["Diff_freq"] = float("nan")
for index, row in res.iterrows():
    if (res.at[index, "Diff_octave"] != 0):
        continue

    xNote = row["X_note"]
    yNote = row["Y_note"]
    xPitch = row["X_pitch"]
    yPitch = row["Y_pitch"]

    xNoteNumFreq = LOWEST_FREQ * HALFTONE_FREQ_COEFF**xNote
    yNoteNumFreq = LOWEST_FREQ * HALFTONE_FREQ_COEFF**yNote
    xPitchHalfTone = xPitch / SMF_HALFTONE_PBVALUE
    yPitchHalfTone = yPitch / SMF_HALFTONE_PBVALUE
    xNoteTrueFreq = xNoteNumFreq * HALFTONE_FREQ_COEFF**xPitchHalfTone
    yNoteTrueFreq = yNoteNumFreq * HALFTONE_FREQ_COEFF**yPitchHalfTone

    res.at[index, "Diff_freq"] = yNoteTrueFreq - xNoteTrueFreq

res["HasDiff_timing"] = res["Diff_timing"] != 0
res["Diff_timing(Beats)"] = res["Diff_timing"].astype(float) / res["TicksPerBeat"].astype(float)
res["HasDiff_program"] = res["Diff_program"] != 0
res["HasDiff_pan"] = res["Diff_pan"] != 0
res["X_panClassification"] = res["X_pan"].apply(getPanClassification)
res["Y_panClassification"] = res["Y_pan"].apply(getPanClassification)
res["X_panIsCenter"] = res["X_pan"] == 64
res["Y_panIsCenter"] = res["Y_pan"] == 64
res["HasDiff_pitch"] = res["Diff_pitch"] != 0
res["HasDiff_ppp"] = res["HasDiff_program"] | res["HasDiff_pitch"] | res["HasDiff_pan"]
res["X_hasPitchBend"] = res["X_pitch"] != 0
res["Y_hasPitchBend"] = res["Y_pitch"] != 0
res["HasDiff_ovVol"] = res["Diff_ovVol"] != 0
res["HasDiff_octave"] = res["Diff_octave"] != 0

# グラフ作成の下準備
plt.rcParams["font.family"] = "MS Gothic"
pd.options.display.precision = 4
fig1, ax1 = plt.subplots(nrows=1, ncols=1, figsize=(20, 20))
fig3, ax3 = plt.subplots(nrows=2, ncols=3, figsize=(120, 60))

# ================
# 詳細な集計
# ================
# 1. ディレイ関係の整理
currentRecord = ""
currentRecordBuf = ""
currentSection = ""
currentSectionStrong = ""
relatedTracksSets = {} #ディレイ関係を持つトラックの集合
relatedTracksSetsStrong = {} #強固なディレイ関係を持つトラックの集合
sequencesUseDelay = [] #ディレイ効果を用いている曲のリスト
sequencesUseDelayStrong = [] #強固なディレイ効果を用いている曲のリスト
relationCount = 0
relationStrongCount = 0

overlapFlags = None
overlapFlagsStrong = None

for row in res.itertuples():
    # ディレイ関係の整理
    currentRecord = row.File + str(row.Section) + str(row.TrackX) + str(row.TrackY) + str(row.Base)
    if (currentRecordBuf == currentRecord):
        continue

    # 強固な関係に関する処理を行うかどうか
    doStrongProcess = row.IsStrong

    # 新しいセクション／新しい曲
    if (currentSection != row.File + str(row.Section)):
        currentSection = row.File + str(row.Section)
        sequencesUseDelay.append(row.File)
        relationCount += 1
        relatedTracksSets[currentSection] = [ {row.TrackX, row.TrackY} ]
        overlapFlags = [ False ]
    # 同じセクションかつ同じ曲
    else:
        # トラック番号の重複を調べる
        overlapExistFlag = False
        overlapFlags = [False for _ in overlapFlags]
        for i, delSet in enumerate(relatedTracksSets[currentSection]):
            # 既存のグループに繋がりがある
            if ((row.TrackX in delSet) or (row.TrackY in delSet)):
                overlapFlags[i] = True
                overlapExistFlag = True  
        if (overlapExistFlag):
            # 重複フラグの立った集合をすべて統合
            newSet = set()
            representativeSetIndex = -1
            for i, flag in enumerate(overlapFlags):
                if (flag):
                    newSet |= relatedTracksSets[currentSection][i]
                    if (representativeSetIndex == -1):
                        representativeSetIndex = i
            # 統合済みの集合に置き換え
            relatedTracksSets[currentSection][representativeSetIndex] = newSet | {row.TrackX, row.TrackY}
            # 不要な集合を削除
            for i in range(len(relatedTracksSets[currentSection]))[::-1]:
                if ((overlapFlags[i]) and (i != representativeSetIndex)):
                    del relatedTracksSets[currentSection][i]
                    del overlapFlags[i]
        else:
            # 新しいグループ作成
            relatedTracksSets[currentSection].append({row.TrackX, row.TrackY})
            overlapFlags.append(False)
            
    # これ以降、強固な関係に関する処理
    if (not doStrongProcess):
        continue
    if (currentSectionStrong != row.File + str(row.Section)):
        currentSectionStrong = row.File + str(row.Section)
        sequencesUseDelayStrong.append(row.File)
        relationStrongCount += 1
        relatedTracksSetsStrong[currentSection] = [ {row.TrackX, row.TrackY} ]
        overlapFlagsStrong = [ False ]
    else:
        # トラック番号の重複を調べる
        overlapExistFlagStrong = False
        overlapFlagsStrong = [False for _ in overlapFlagsStrong]
        for i, delSet in enumerate(relatedTracksSetsStrong[currentSection]):
            # 既存のグループに繋がりがある
            if ((row.TrackX in delSet) or (row.TrackY in delSet)):
                overlapFlagsStrong[i] = True
                overlapExistFlagStrong = True
        if (overlapExistFlagStrong):
            # 重複フラグの立った集合をすべて統合
            newSetStrong = set()
            representativeSetIndexStrong = -1
            for i, flag in enumerate(overlapFlagsStrong):
                if (flag):
                    newSetStrong |= relatedTracksSetsStrong[currentSection][i]
                    if (representativeSetIndexStrong == -1):
                        representativeSetIndexStrong = i
            # 統合済みの集合に置き換え
            relatedTracksSetsStrong[currentSection][representativeSetIndexStrong] = newSetStrong | {row.TrackX, row.TrackY}
            # 不要な集合を削除
            for i in range(len(relatedTracksSetsStrong[currentSection]))[::-1]:
                if ((overlapFlagsStrong[i]) and (i != representativeSetIndexStrong)):
                    del relatedTracksSetsStrong[currentSection][i]
                    del overlapFlagsStrong[i]
        else:
            # 新しいグループ作成
            relatedTracksSetsStrong[currentSection].append({row.TrackX, row.TrackY})
            overlapFlagsStrong.append(False)

# 重複排除
sequencesUseDelay = list(dict.fromkeys(sequencesUseDelay))
sequencesUseDelayStrong = list(dict.fromkeys(sequencesUseDelayStrong))

# 2. データ概観
# ディレイ使用割合
print(f"ディレイを用いている曲の割合: {len(sequencesUseDelay) / analyzedFilesCount}")
print(f"強固なディレイを用いている曲の割合: {len(sequencesUseDelayStrong) / analyzedFilesCount}")
print(f"強固なディレイ関係の割合: {relationStrongCount / relationCount} = {relationStrongCount} / {relationCount}")

# ディレイ関係にあるトラックの集合が、何トラックからなるか集計
trackSetsCount = [0] * (SMF_TRACK_MAXCOUNT + 1)
trackSetsStrongCount = [0] * (SMF_TRACK_MAXCOUNT + 1)
for sets in relatedTracksSets.values():
    for s in sets:
        trackSetsCount[len(s)] += 1
for sets in relatedTracksSetsStrong.values():
    for s in sets:
        trackSetsStrongCount[len(s)] += 1
trackSetsCountSum = sum(trackSetsCount)
trackSetsStrongCountSum = sum(trackSetsStrongCount)

# 平均値、標準偏差を求める
trackSetsCountMean = 0
trackSetsStrongCountMean = 0
for i in range(SMF_TRACK_MAXCOUNT + 1):
    trackSetsCountMean += trackSetsCount[i] * i
    trackSetsStrongCountMean += trackSetsStrongCount[i] * i
trackSetsCountMean /= trackSetsCountSum
trackSetsStrongCountMean /= trackSetsStrongCountSum
trackSetsCountSigma = 0
trackSetsStrongCountSigma = 0
for i in range(SMF_TRACK_MAXCOUNT + 1):
    trackSetsCountSigma += trackSetsCount[i] * (i - trackSetsCountMean)**2
    trackSetsStrongCountSigma += trackSetsStrongCount[i] * (i - trackSetsStrongCountMean)**2
trackSetsCountSigma /= trackSetsCountSum
trackSetsStrongCountSigma /= trackSetsStrongCountSum
trackSetsCountSigma **= 0.5
trackSetsStrongCountSigma **= 0.5

# 割合を求める
for i in range(SMF_TRACK_MAXCOUNT):
    trackSetsCount[i] = trackSetsCount[i] / trackSetsCountSum
    trackSetsStrongCount[i] = trackSetsStrongCount[i] / trackSetsStrongCountSum

print(f"ディレイ関係にあるトラックの集合が何トラック含むか: {trackSetsCount}")
print(f"平均値: {trackSetsCountMean}, 標準偏差: {trackSetsCountSigma}")
print(f"強固なディレイ関係にあるトラックの集合が何トラック含むか: {trackSetsStrongCount}")
print(f"平均値: {trackSetsStrongCountMean}, 標準偏差: {trackSetsStrongCountSigma}")

xAxis = np.arange(2, SMF_TRACK_MAXCOUNT + 1, 1)
p1 = ax1.bar(xAxis, trackSetsCount[2:], align="edge", width=-0.3,
             label=f"すべてのディレイ関係\n平均値:{trackSetsCountMean:.3f}\n標準偏差:{trackSetsCountSigma:.3f}")
p2 = ax1.bar(xAxis, trackSetsStrongCount[2:], align="edge", width=0.3,
             label=f"強固なディレイ関係\n平均値:{trackSetsStrongCountMean:.3f}\n標準偏差:{trackSetsStrongCountSigma:.3f}")
ax1.set_xticks(xAxis)
ax1.set_xticklabels(xAxis, rotation=90)
ax1.bar_label(p1, fmt="%.3f", padding=8, fontsize=8)
ax1.bar_label(p2, fmt="%.3f", fontsize=8)
ax1.legend(fontsize=16)
fig1.savefig("result/fig1.png", bbox_inches="tight")


# 3. 詳細な統計（強固なディレイ関係についてのみ）
# 1セットのトラック組み合わせは、1回しかカウントしない
resStrong = res[(res["IsStrong"] == True) & (res["Base"] == "X")]
resStrongZ = res[(res["IsStrong"] == True) & (res["Base"] == "X") & (res["HasDiff_timing"] == False)]
resStrongNZ = res[(res["IsStrong"] == True) & (res["Base"] == "X") & (res["HasDiff_timing"] == True)]

print(f"resStrong.shape: {resStrong.shape}")
print(f"resStrongZ.shape: {resStrongZ.shape}")
print(f"resStrongNZ.shape: {resStrongNZ.shape}")


# 統計を求める列
statCols = [
    # 数量変数
    "X_pan", "X_pitch", "X_mainVol", "X_expression", "X_velocity", "X_ovVol",
    "Y_pan", "Y_pitch", "Y_mainVol", "Y_expression", "Y_velocity", "Y_ovVol",
    "Diff_timing(MicroSeconds)", "Diff_timing(Beats)", 
    "Diff_pitch", "Diff_freq", "Diff_pan",
    "Diff_mainVol", "Diff_expression", "Diff_velocity", "Diff_ovVol",
    "Diff_octave",
    "Diff_program(group)",
    "X_panClassification", "Y_panClassification",
    # 名義尺度
    "HasDiff_timing", "HasDiff_program", "HasDiff_pan", "HasDiff_pitch", "HasDiff_ppp",
    "HasDiff_ovVol", "HasDiff_octave",
    "X_panIsCenter", "Y_panIsCenter", "X_hasPitchBend", "Y_hasPitchBend"
]

# 記述統計
# 3-1. 列単体
# 全部
outputStat(statCols, resStrong, "all_")
# ディレイ無しの場合
outputStat(statCols, resStrongZ, "Z_")
# ディレイありの場合
outputStat(statCols, resStrongNZ, "NZ_")

# 3-2. クロス集計
def outputCrossTable(_resCt: pd.DataFrame, _type: str):
    print(f"===={_type}====")
    # 先行音パン分類と後続音パン分類
    crossTable = pd.crosstab(_resCt["X_panClassification"], _resCt["Y_panClassification"], normalize=True)
    print(crossTable)
    # 先行音パンと後続音パン
    crossTable = pd.crosstab(_resCt["X_panIsCenter"], _resCt["Y_panIsCenter"], normalize=True)
    print(crossTable)
    # 先行音ピッチと後続音ピッチ
    crossTable = pd.crosstab(_resCt["X_hasPitchBend"], _resCt["Y_hasPitchBend"], normalize=True)
    print(crossTable)
    # 音色差とピッチ差
    crossTable = pd.crosstab(_resCt["HasDiff_pitch"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # 音色差とパン差
    crossTable = pd.crosstab(_resCt["HasDiff_pan"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # 音色差と音量差
    crossTable = pd.crosstab(_resCt["HasDiff_ovVol"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # 音色差とオクターブ差
    crossTable = pd.crosstab(_resCt["HasDiff_octave"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # 音量差とパン差
    crossTable = pd.crosstab(_resCt["HasDiff_ovVol"], _resCt["HasDiff_pan"], normalize=True)
    print(crossTable)
    # 音量差とピッチ差
    crossTable = pd.crosstab(_resCt["HasDiff_ovVol"], _resCt["HasDiff_pitch"], normalize=True)
    print(crossTable)
    
    print("============")

# 全部
outputCrossTable(resStrong, "all")
outputCrossTable(resStrongZ, "Z")
outputCrossTable(resStrongNZ, "NZ")


# 3-3. 相関係数
# 全体
resCorr = resStrong[statCols].corr()
resCorr.to_csv("result/corr_all.csv")
sns.heatmap(resCorr, ax=ax3[0, 0], vmax=1, vmin=-1, center=0)
pg = sns.pairplot(resStrong[statCols])
pg.savefig("result/pp_all.png")

# ディレイなし
resCorr = resStrongZ[statCols].corr()
resCorr.to_csv("result/corr_Z.csv")
sns.heatmap(resCorr, ax=ax3[0, 1], vmax=1, vmin=-1, center=0)
pg = sns.pairplot(resStrongZ[statCols])
pg.savefig("result/pp_Z.png")

# ディレイあり
resCorr = resStrongNZ[statCols].corr()
resCorr.to_csv("result/corr_NZ.csv")
sns.heatmap(resCorr, ax=ax3[0, 2], vmax=1, vmin=-1, center=0)
pg = sns.pairplot(resStrongNZ[statCols])
pg.savefig("result/pp_NZ.png")

# 図保存
fig3.savefig("result/fig3.png", bbox_inches="tight")
