#!python3.10
# coding: shift_jis

import sys
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from distutils.util import strtobool

#================
# �萔
#================
# SMF�̍ő�g���b�N��
SMF_TRACK_MAXCOUNT = 16

# SMF�ɂ����Ĕ����ɑΉ�����s�b�`�x���h�l
SMF_HALFTONE_PBVALUE = 8192

# ���g��
LOWEST_FREQ = 8.1758
HALFTONE_FREQ_COEFF = 2 ** (1/12)


#================
# �֐�
#================
# �p���̐��l����p���̎�ނ𔻕�
def getPanClassification(_pan):
    if (_pan == 64):
        return 0 #C
    elif (_pan == 127):
        return 2 #R�[
    elif (_pan == 0):
        return -2 #L�[
    elif(_pan > 64):
        return 1 #R
    else:
        return -1 #L

# ���͂��������Ȑ����擾
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

# �x�����z���쐬
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

    return pd.DataFrame({"�K���l": (bins[1:] + bins[:-1]) / 2,
                         "�x��": hist,
                         "�ݐϓx��": cumSum,
                         "���Γx��": hist / cumSum[-1],
                         "�ݐϑ��Γx��": cumSum / cumSum[-1]},
                        index=pd.Index([f"{bins[i]}�ȏ�{bins[i+1]}����"
                                        for i in range(hist.size)],
                                       name="�K��"))

# ���v�����܂Ƃ߂ďo��
def outputStat(_statCols, _res: pd.DataFrame, _figFileBase: str):
    for c in _statCols:
        # �v��
        s_res = _res[c]
        # ���ϒl
        s_mean = s_res.mean()
        # �W���΍�
        s_sigma = s_res.std(ddof=0)
        # �����l
        s_median = s_res.median()
        # �ő�l�E�ŏ��l
        s_maxdata = s_res.max()
        s_mindata = s_res.min()
        # �ŕp�l
        s_mode = s_res.mode()
        # �x�����z
        # �K����
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
        # �������ǂ���
        s_isInt = True
        if ((c == "X_ovVol") or (c == "X_pitchFreq")
            or (c == "Y_ovVol") or (c == "Y_pitchFreq")
            or (c == "Diff_timing(MicroSeconds)") or (c == "Diff_ovVol")):
            s_isInt = False
        # �ŏ��l
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
        # �ő�l
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

        # �O���t�쐬
        # �e�L�X�g�f�[�^
        s_labelText = f"���ϒl:{s_mean:.3f}\n�W���΍�:{s_sigma:.3f}\n�����l:{s_median:.3f}\n"
        s_labelText += f"�ő�l{s_maxdata:.3f}:\n�ŏ��l:{s_mindata:.3f}\n"
        s_vc = s_res.value_counts(normalize=True)
        if (c == "Diff_timing(Beats)"):
            s_vc.to_csv(f"result/{_figFileBase}{c}_value_counts.csv")
        for m in s_mode:
            s_labelText += f"�ŕp�l:{m:.3f}, ���Εp�x:{s_vc.loc[m]:.3f}\n"
        if (s_classWidth is not None):
            s_labelText += f"�K����:{s_classWidth:.3f}"
        # �O���t�{��
        s_fd = FreqDist(s_res, s_classWidth, s_isInt, s_min, s_max)
        s_fig, s_ax = plt.subplots(nrows=1, ncols=1, figsize=(max(round(len(s_fd)*1.2), 20), 20))

        p = s_ax.bar(x=s_fd["�K���l"], height=s_fd["���Γx��"], ec="k", lw=1,
                    width=s_classWidth,
                    label=s_labelText)
        s_ax.bar_label(p, fmt="%.3f", fontsize=10)
        s_ax.set_xticks(s_fd["�K���l"])
        s_ax.set_title(c)
        s_ax.legend(fontsize=16)

        # �}�ۑ�
        s_fig.savefig(f"result/{_figFileBase}{c}.png", bbox_inches="tight")
        # print(f"saved: {_figFileBase}{c}.png")


# ���֔�
def CorrelationV(x, y):
    variation = ((y - y.mean()) ** 2).sum()
    interClass = sum([((y[x == i] - y[x == i].mean()) ** 2).sum() for i in np.unique(x)])
    corrRatio = interClass / variation
    return 1 - corrRatio

# ================
# ���C������
# ================
logFilePath = "exlog.txt"
resultFilePath = "out.csv"

# ���͂��������Ȑ����擾
analyzedFilesCount = getanalyzedFilesCount(logFilePath)

# ���͌��ʂ���f�[�^�t���[���쐬
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

# �f�B���C�̎����ԁi�}�C�N���b�P�ʁj�����߂�
# ������ = �e�B�b�N�P�ʂ̎��� * �e���|(�l������������̃}�C�N���b��) / ����\(�l������������̃e�B�b�N��)
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

# �O���t�쐬�̉�����
plt.rcParams["font.family"] = "MS Gothic"
pd.options.display.precision = 4
fig1, ax1 = plt.subplots(nrows=1, ncols=1, figsize=(20, 20))
fig3, ax3 = plt.subplots(nrows=2, ncols=3, figsize=(120, 60))

# ================
# �ڍׂȏW�v
# ================
# 1. �f�B���C�֌W�̐���
currentRecord = ""
currentRecordBuf = ""
currentSection = ""
currentSectionStrong = ""
relatedTracksSets = {} #�f�B���C�֌W�����g���b�N�̏W��
relatedTracksSetsStrong = {} #���łȃf�B���C�֌W�����g���b�N�̏W��
sequencesUseDelay = [] #�f�B���C���ʂ�p���Ă���Ȃ̃��X�g
sequencesUseDelayStrong = [] #���łȃf�B���C���ʂ�p���Ă���Ȃ̃��X�g
relationCount = 0
relationStrongCount = 0

overlapFlags = None
overlapFlagsStrong = None

for row in res.itertuples():
    # �f�B���C�֌W�̐���
    currentRecord = row.File + str(row.Section) + str(row.TrackX) + str(row.TrackY) + str(row.Base)
    if (currentRecordBuf == currentRecord):
        continue

    # ���łȊ֌W�Ɋւ��鏈�����s�����ǂ���
    doStrongProcess = row.IsStrong

    # �V�����Z�N�V�����^�V������
    if (currentSection != row.File + str(row.Section)):
        currentSection = row.File + str(row.Section)
        sequencesUseDelay.append(row.File)
        relationCount += 1
        relatedTracksSets[currentSection] = [ {row.TrackX, row.TrackY} ]
        overlapFlags = [ False ]
    # �����Z�N�V������������
    else:
        # �g���b�N�ԍ��̏d���𒲂ׂ�
        overlapExistFlag = False
        overlapFlags = [False for _ in overlapFlags]
        for i, delSet in enumerate(relatedTracksSets[currentSection]):
            # �����̃O���[�v�Ɍq���肪����
            if ((row.TrackX in delSet) or (row.TrackY in delSet)):
                overlapFlags[i] = True
                overlapExistFlag = True  
        if (overlapExistFlag):
            # �d���t���O�̗������W�������ׂē���
            newSet = set()
            representativeSetIndex = -1
            for i, flag in enumerate(overlapFlags):
                if (flag):
                    newSet |= relatedTracksSets[currentSection][i]
                    if (representativeSetIndex == -1):
                        representativeSetIndex = i
            # �����ς݂̏W���ɒu������
            relatedTracksSets[currentSection][representativeSetIndex] = newSet | {row.TrackX, row.TrackY}
            # �s�v�ȏW�����폜
            for i in range(len(relatedTracksSets[currentSection]))[::-1]:
                if ((overlapFlags[i]) and (i != representativeSetIndex)):
                    del relatedTracksSets[currentSection][i]
                    del overlapFlags[i]
        else:
            # �V�����O���[�v�쐬
            relatedTracksSets[currentSection].append({row.TrackX, row.TrackY})
            overlapFlags.append(False)
            
    # ����ȍ~�A���łȊ֌W�Ɋւ��鏈��
    if (not doStrongProcess):
        continue
    if (currentSectionStrong != row.File + str(row.Section)):
        currentSectionStrong = row.File + str(row.Section)
        sequencesUseDelayStrong.append(row.File)
        relationStrongCount += 1
        relatedTracksSetsStrong[currentSection] = [ {row.TrackX, row.TrackY} ]
        overlapFlagsStrong = [ False ]
    else:
        # �g���b�N�ԍ��̏d���𒲂ׂ�
        overlapExistFlagStrong = False
        overlapFlagsStrong = [False for _ in overlapFlagsStrong]
        for i, delSet in enumerate(relatedTracksSetsStrong[currentSection]):
            # �����̃O���[�v�Ɍq���肪����
            if ((row.TrackX in delSet) or (row.TrackY in delSet)):
                overlapFlagsStrong[i] = True
                overlapExistFlagStrong = True
        if (overlapExistFlagStrong):
            # �d���t���O�̗������W�������ׂē���
            newSetStrong = set()
            representativeSetIndexStrong = -1
            for i, flag in enumerate(overlapFlagsStrong):
                if (flag):
                    newSetStrong |= relatedTracksSetsStrong[currentSection][i]
                    if (representativeSetIndexStrong == -1):
                        representativeSetIndexStrong = i
            # �����ς݂̏W���ɒu������
            relatedTracksSetsStrong[currentSection][representativeSetIndexStrong] = newSetStrong | {row.TrackX, row.TrackY}
            # �s�v�ȏW�����폜
            for i in range(len(relatedTracksSetsStrong[currentSection]))[::-1]:
                if ((overlapFlagsStrong[i]) and (i != representativeSetIndexStrong)):
                    del relatedTracksSetsStrong[currentSection][i]
                    del overlapFlagsStrong[i]
        else:
            # �V�����O���[�v�쐬
            relatedTracksSetsStrong[currentSection].append({row.TrackX, row.TrackY})
            overlapFlagsStrong.append(False)

# �d���r��
sequencesUseDelay = list(dict.fromkeys(sequencesUseDelay))
sequencesUseDelayStrong = list(dict.fromkeys(sequencesUseDelayStrong))

# 2. �f�[�^�T��
# �f�B���C�g�p����
print(f"�f�B���C��p���Ă���Ȃ̊���: {len(sequencesUseDelay) / analyzedFilesCount}")
print(f"���łȃf�B���C��p���Ă���Ȃ̊���: {len(sequencesUseDelayStrong) / analyzedFilesCount}")
print(f"���łȃf�B���C�֌W�̊���: {relationStrongCount / relationCount} = {relationStrongCount} / {relationCount}")

# �f�B���C�֌W�ɂ���g���b�N�̏W�����A���g���b�N����Ȃ邩�W�v
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

# ���ϒl�A�W���΍������߂�
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

# ���������߂�
for i in range(SMF_TRACK_MAXCOUNT):
    trackSetsCount[i] = trackSetsCount[i] / trackSetsCountSum
    trackSetsStrongCount[i] = trackSetsStrongCount[i] / trackSetsStrongCountSum

print(f"�f�B���C�֌W�ɂ���g���b�N�̏W�������g���b�N�܂ނ�: {trackSetsCount}")
print(f"���ϒl: {trackSetsCountMean}, �W���΍�: {trackSetsCountSigma}")
print(f"���łȃf�B���C�֌W�ɂ���g���b�N�̏W�������g���b�N�܂ނ�: {trackSetsStrongCount}")
print(f"���ϒl: {trackSetsStrongCountMean}, �W���΍�: {trackSetsStrongCountSigma}")

xAxis = np.arange(2, SMF_TRACK_MAXCOUNT + 1, 1)
p1 = ax1.bar(xAxis, trackSetsCount[2:], align="edge", width=-0.3,
             label=f"���ׂẴf�B���C�֌W\n���ϒl:{trackSetsCountMean:.3f}\n�W���΍�:{trackSetsCountSigma:.3f}")
p2 = ax1.bar(xAxis, trackSetsStrongCount[2:], align="edge", width=0.3,
             label=f"���łȃf�B���C�֌W\n���ϒl:{trackSetsStrongCountMean:.3f}\n�W���΍�:{trackSetsStrongCountSigma:.3f}")
ax1.set_xticks(xAxis)
ax1.set_xticklabels(xAxis, rotation=90)
ax1.bar_label(p1, fmt="%.3f", padding=8, fontsize=8)
ax1.bar_label(p2, fmt="%.3f", fontsize=8)
ax1.legend(fontsize=16)
fig1.savefig("result/fig1.png", bbox_inches="tight")


# 3. �ڍׂȓ��v�i���łȃf�B���C�֌W�ɂ��Ă̂݁j
# 1�Z�b�g�̃g���b�N�g�ݍ��킹�́A1�񂵂��J�E���g���Ȃ�
resStrong = res[(res["IsStrong"] == True) & (res["Base"] == "X")]
resStrongZ = res[(res["IsStrong"] == True) & (res["Base"] == "X") & (res["HasDiff_timing"] == False)]
resStrongNZ = res[(res["IsStrong"] == True) & (res["Base"] == "X") & (res["HasDiff_timing"] == True)]

print(f"resStrong.shape: {resStrong.shape}")
print(f"resStrongZ.shape: {resStrongZ.shape}")
print(f"resStrongNZ.shape: {resStrongNZ.shape}")


# ���v�����߂��
statCols = [
    # ���ʕϐ�
    "X_pan", "X_pitch", "X_mainVol", "X_expression", "X_velocity", "X_ovVol",
    "Y_pan", "Y_pitch", "Y_mainVol", "Y_expression", "Y_velocity", "Y_ovVol",
    "Diff_timing(MicroSeconds)", "Diff_timing(Beats)", 
    "Diff_pitch", "Diff_freq", "Diff_pan",
    "Diff_mainVol", "Diff_expression", "Diff_velocity", "Diff_ovVol",
    "Diff_octave",
    "Diff_program(group)",
    "X_panClassification", "Y_panClassification",
    # ���`�ړx
    "HasDiff_timing", "HasDiff_program", "HasDiff_pan", "HasDiff_pitch", "HasDiff_ppp",
    "HasDiff_ovVol", "HasDiff_octave",
    "X_panIsCenter", "Y_panIsCenter", "X_hasPitchBend", "Y_hasPitchBend"
]

# �L�q���v
# 3-1. ��P��
# �S��
outputStat(statCols, resStrong, "all_")
# �f�B���C�����̏ꍇ
outputStat(statCols, resStrongZ, "Z_")
# �f�B���C����̏ꍇ
outputStat(statCols, resStrongNZ, "NZ_")

# 3-2. �N���X�W�v
def outputCrossTable(_resCt: pd.DataFrame, _type: str):
    print(f"===={_type}====")
    # ��s���p�����ނƌ㑱���p������
    crossTable = pd.crosstab(_resCt["X_panClassification"], _resCt["Y_panClassification"], normalize=True)
    print(crossTable)
    # ��s���p���ƌ㑱���p��
    crossTable = pd.crosstab(_resCt["X_panIsCenter"], _resCt["Y_panIsCenter"], normalize=True)
    print(crossTable)
    # ��s���s�b�`�ƌ㑱���s�b�`
    crossTable = pd.crosstab(_resCt["X_hasPitchBend"], _resCt["Y_hasPitchBend"], normalize=True)
    print(crossTable)
    # ���F���ƃs�b�`��
    crossTable = pd.crosstab(_resCt["HasDiff_pitch"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # ���F���ƃp����
    crossTable = pd.crosstab(_resCt["HasDiff_pan"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # ���F���Ɖ��ʍ�
    crossTable = pd.crosstab(_resCt["HasDiff_ovVol"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # ���F���ƃI�N�^�[�u��
    crossTable = pd.crosstab(_resCt["HasDiff_octave"], _resCt["Diff_program(group)"], normalize=True)
    print(crossTable)
    # ���ʍ��ƃp����
    crossTable = pd.crosstab(_resCt["HasDiff_ovVol"], _resCt["HasDiff_pan"], normalize=True)
    print(crossTable)
    # ���ʍ��ƃs�b�`��
    crossTable = pd.crosstab(_resCt["HasDiff_ovVol"], _resCt["HasDiff_pitch"], normalize=True)
    print(crossTable)
    
    print("============")

# �S��
outputCrossTable(resStrong, "all")
outputCrossTable(resStrongZ, "Z")
outputCrossTable(resStrongNZ, "NZ")


# 3-3. ���֌W��
# �S��
resCorr = resStrong[statCols].corr()
resCorr.to_csv("result/corr_all.csv")
sns.heatmap(resCorr, ax=ax3[0, 0], vmax=1, vmin=-1, center=0)
pg = sns.pairplot(resStrong[statCols])
pg.savefig("result/pp_all.png")

# �f�B���C�Ȃ�
resCorr = resStrongZ[statCols].corr()
resCorr.to_csv("result/corr_Z.csv")
sns.heatmap(resCorr, ax=ax3[0, 1], vmax=1, vmin=-1, center=0)
pg = sns.pairplot(resStrongZ[statCols])
pg.savefig("result/pp_Z.png")

# �f�B���C����
resCorr = resStrongNZ[statCols].corr()
resCorr.to_csv("result/corr_NZ.csv")
sns.heatmap(resCorr, ax=ax3[0, 2], vmax=1, vmin=-1, center=0)
pg = sns.pairplot(resStrongNZ[statCols])
pg.savefig("result/pp_NZ.png")

# �}�ۑ�
fig3.savefig("result/fig3.png", bbox_inches="tight")
