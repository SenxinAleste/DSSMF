#!python3.10
# coding: shift_jis

import os
import sys
import copy
import mido
import collections
from hashlib import sha256
from enum import IntEnum, auto

#================
# �萔
#================
# SMF�̍ő�g���b�N��
SMF_TRACK_MAXCOUNT = 16
# �R���g���[���`�F���W�̔ԍ�
CONTROL_RPN_DATA_MSB = 6
CONTROL_MAINVOLUME = 7
CONTROL_PANPOT = 10
CONTROL_EXPRESSION = 11
CONTROL_RPN_LSB = 100
CONTROL_RPN_MSB = 101


# �f�B���C�ƔF�߂�ő�̃m�[�g�I���Ԋu�i�����P�ʁj
DELAY_MAX_BEAT = 0.9999
# �f�B���C�֌W�X�R�A�����̒l�ȏゾ������L�^
DELAY_RELATION_SCORE_THRESHOLD = 0.9

# �t�����̃f�t�H���g�l
TEMPO_DEFAULT = 500000 #BPM120
PROGRAM_DEFAULT = 0
PBSENS_DEFAULT = 2
PITCH_DEFAULT = 0
PAN_CENTER = 64
PAN_DEFAULT = PAN_CENTER
MAINVOLUME_DEFAULT = 100
EXPRESSION_DEFAULT = 127

# DiscStation�̍���
ISSUE_MIN = 12
ISSUE_MAX = 27

#================
# �N���X
#================
class SurvayTargetMessages:
    """�����ΏۂƂȂ�A�t��������i���F���j"""
    # ��{�I�ɁA�ȉ���3�̏���ێ�����B
    # �E�e���|
    # �E���F
    # �E�s�b�`�x���h�Z���V�e�B�r�e�B
    # �E�s�b�`�x���h
    # �E�p���|�b�g
    # �E���C���{�����[��
    # �E�G�N�X�v���b�V����
    def __init__(self):
        self.tempo = None
        self.program = None
        self.pbsens = 2
        self.pitch = None
        self.pan = None
        self.mainVol = None
        self.express = None

    def __str__(self):
        return f"prg:{self.program}, pit:{self.pitch}, pan:{self.pan}"

class MidiMsgInfo:
    """MIDI���b�Z�[�W���p�b�N�������́i��Ύ����ł̔����^�C�~���O��ێ��B
        �I�v�V�����ŕt�����A��s�^�㑱���鉹��ێ��j"""
    def __init__(self, _msg: mido.Message, _tick: int, _addInfo: SurvayTargetMessages =None):
        self.msg = _msg
        self.tick = _tick
        self.addInfo = copy.deepcopy(_addInfo)
        self.following = None
        self.preceding = None
    
    def __str__(self):
        return f"AbsTick {self.tick} <{self.msg}>"


#================
# MIDI�֘A�̔ėp�֐�
#================
# mido��MetaMessage�I�u�W�F�N�g����Ashift_jis�ŕ���������o���֐�
def getTextFromMetaMessage(_msg: mido.MetaMessage):
    try:
        text = _msg.bin()[3:].decode('shift_jis')
    except UnicodeDecodeError:
        text = _msg.bin()[3:]
    return text

# SMF�t�H�[�}�b�g1��0�ɕϊ�����֐�
def SMF1to0(_midOrg: mido.MidiFile):
    # �t�H�[�}�b�g�m�F
    if (_midOrg.type != 1):
        print("[Error] SMF format != 1")
        return _midOrg

    # �ϊ�
    midCnv = mido.MidiFile(type=0)
    midCnv.add_track()
    midCnv.tracks[0] = mido.merge_tracks(_midOrg.tracks)

    return midCnv

# SMF�t�H�[�}�b�g0��1�ɕϊ�����֐�
# 0�g���b�N�ڂɂ��ׂẴ��^���b�Z�[�W�A
# n�in=1~16�j�g���b�N�ڂ�n�`�����l���̏�񂷂ׂĂ�����
# ��Tick�����擾
def SMF0to1AndGetTotalTicks(_midOrg: mido.MidiFile):
    # �t�H�[�}�b�g�m�F
    if (_midOrg.type != 0):
        print("[Error] SMF format != 0")
        return _midOrg

    midCnvTrackCount = SMF_TRACK_MAXCOUNT + 1
    midCnv = mido.MidiFile(type=1)
    midCnv.ticks_per_beat = _midOrg.ticks_per_beat #�w�b�_�ݒ�
    for _ in range (midCnvTrackCount):
        midCnv.add_track()
    # �ϊ��̂��߂ɋL�^����Tick��
    tickInTrack = [0] * midCnvTrackCount # �ϊ���SMF�̂���g���b�N���ɂ����āA����Ō���ɂ���C�x���g�����������^�C�~���O
    tickGlobal = 0 # �S�̂Ői��Tick�����L�^
    # sysex�̗L��
    midCnv.hasSysex = False

    # �ϊ�
    for msg in _midOrg.tracks[0]:
        # Tick��i�߂�
        tickGlobal += msg.time
        # ���^���b�Z�[�W�E�V�X�e���G�N�X�N���[�V�u
        if (msg.is_meta or (msg.type == "sysex")):
            # �g���b�N0�֊i�[
            msgNew = msg.copy(time = tickGlobal - tickInTrack[0])
            midCnv.tracks[0].append(msgNew)
            tickInTrack[0] = tickGlobal

            # sysex������ꍇ�L�^
            if (msg.type == "sysex"):
                midCnv.hasSysex = True
                print(f"[Info] SysEx exist: {msg}")
        # ���^���b�Z�[�W�ȊO�i�`�����l���w�肪����j
        else:
            ch = msg.channel + 1
            msgNew = msg.copy(time = tickGlobal - tickInTrack[ch])
            midCnv.tracks[ch].append(msgNew)
            tickInTrack[ch] = tickGlobal
    
    midCnv.totalTicks = tickGlobal
    
    return midCnv

# �Ȗ��\��
def getSequenceName(_midData: mido.MidiFile):
    for msg in _midData.tracks[0]:
        if (msg.type == "track_name"):
            return getTextFromMetaMessage(msg)

# ���q�擾
def getTimeSignature(_midData: mido.MidiFile):
    timeSigNume = 4
    timeSigDeno = 4
    for msg in _midData.tracks[0]:
        # ���q�̏��
        if (msg.type == "time_signature"):
            timeSigNume = msg.numerator
            timeSigDeno = msg.denominator
            if (msg.notated_32nd_notes_per_beat != 32/4):
                print(f"[Error] Irregular notated_32nd_notes_per_beat: {msg.notated_32nd_notes_per_beat}")
            break
    return (timeSigNume, timeSigDeno)


#================
# ���͊֐��i���i�j
#================
# �Z�N�V�����J�n���ߎ擾
def getSectionStartBars(_midData: mido.MidiFile, _ticksPerBar: int):
    sectionStartBars = [1]

    for i, track in enumerate(_midData.tracks[1:], start=1):
        globalTick = 0 #�g���b�N���ŉ�Tick�i�񂾂�
        currentProgram = 0 #���݂̃v���O�����i���F�j
        noteOnExistPre = False #�g���b�N���Ńm�[�g�I�����������Ƃ��A�܂����̃t���O��True�ɂ���
        noteOnExist = False #noteOnExistPre��True�ɂȂ�����A1Tick�ȏ�o�����炱�̃t���O��True�ɂ���
        # ���b�Z�[�W����
        for msg in track:
            globalTick += msg.time
            if (noteOnExistPre and msg.time > 0):
                noteOnExist = True
            # �v���O�����`�F���W
            if (msg.type == "program_change"):
                if (noteOnExist and currentProgram != msg.program):
                    # �v���O�����`�F���W�ȑO�Ƀm�[�g�I����1�ł����݂���i�������ւ��ɂ�����j�Ȃ�A
                    # �`�F���W�̂������^�C�~���O�̍Ŋ��̏��ߋ�؂���L�^
                    startPointTmp = round(globalTick / _ticksPerBar) + 1
                    if (startPointTmp not in sectionStartBars):
                        sectionStartBars.append(startPointTmp)
                currentProgram = msg.program
            # �m�[�g�I��
            elif (msg.type == "note_on"):
                noteOnExistPre = True
    sectionStartBars.sort()
    sectionStartBars.append(sys.maxsize)
    return sectionStartBars

# MidiMessageWithAbsTime�̔z��i���n�񏇁j���󂯎��A�����m�[�g�I���������߂�
# �����m�[�g�I�����Ƃ́A�����̃m�[�g�I����1�Ɛ������ۂ́A�m�[�g�I���̐�
def getNetNoteCount(_MidiMessageWithAbsTimeList):
    tickTmp = -1
    result = 0
    for msgWithAbsTime in _MidiMessageWithAbsTimeList:
        if (tickTmp != msgWithAbsTime.tick):
            result += 1
            tickTmp = msgWithAbsTime.tick
    return result

# �m�[�g�I���̏��𒊏o���AnoteOnInfo�ɂ܂Ƃ߂ĕԂ�
def extractNoteOnInfo(
        _midData: mido.MidiFile,
        _sectionStartBars,
        _ticksPerBar: int
):
    # �m�[�g�I�������i�[����O�����z��
    noteOnInfo = [[[] for j in range(len(_midData.tracks))] for i in range(len(_sectionStartBars))]

    # �e���|���߂𒊏o
    tempoMsgInfos = []
    if (True):
        # �g���b�N���ŉ�Tick�i�񂾂�
        globalTick = 0
        # �w���g���b�N���̃��b�Z�[�W�𑖍�
        for msg in _midData.tracks[0]:
            # �g���b�N��Tick��i�߂�
            globalTick += msg.time
            # �e���|�ݒ�
            if (msg.type == "set_tempo"):
                tempoMsgInfos.append(MidiMsgInfo(msg, globalTick))
    
    # �e�g���b�N����A�m�[�g�I���i�x���V�e�B0�͏����j�̏��𒊏o
    # �����ɁA���F�E�s�b�`�x���h�E�p������t�����Ƃ��ċL�^
    for i, track in enumerate(_midData.tracks[1:], start=1):
        # ���Y���g���b�N�͖���
        if (i == 10):
            continue

        # �g���b�N���ŉ�Tick�i�񂾂�
        globalTick = 0
        # ���݂̃Z�N�V�����ԍ�
        currentSectionIndex = 0
        # ���݂̕t�����
        currentAddInfo = SurvayTargetMessages()
        # RPN�p�̈ꎞ�ϐ�
        tmpRPN = [-1, -1]
        tmpRPNData = [-1, -1]

        # �g���b�N���̃��b�Z�[�W�𑖍�
        for msg in track:
            # �g���b�N��Tick��i�߂�
            globalTick += msg.time
            # �Z�N�V�����̐؂�ւ��ɓ��B������A�Z�N�V�����ԍ����X�V
            if (globalTick >= _sectionStartBars[currentSectionIndex + 1] * _ticksPerBar):
                currentSectionIndex += 1
            # �e���|���߂ɓ��B������AcurrentAddInfo���X�V
            for tempoMsgInfo in tempoMsgInfos:
                if (globalTick >= tempoMsgInfo.tick):
                    currentAddInfo.tempo = tempoMsgInfo
            
            # �m�[�g�I���i�x���V�e�B0�������j
            if ((msg.type == "note_on") and (msg.velocity != 0)):
                noteOnInfo[currentSectionIndex][i].append(
                    MidiMsgInfo(msg, globalTick, currentAddInfo)
                )
            # ���F
            elif (msg.type == "program_change"):
                currentAddInfo.program = MidiMsgInfo(msg, globalTick)
            # �s�b�`�x���h
            elif (msg.type == "pitchwheel"):
                currentAddInfo.pitch = MidiMsgInfo(msg, globalTick)
            # �p���|�b�g
            elif (msg.is_cc(CONTROL_PANPOT)):
                currentAddInfo.pan = MidiMsgInfo(msg, globalTick)
            # ���C���{�����[��
            elif (msg.is_cc(CONTROL_MAINVOLUME)):
                currentAddInfo.pan = MidiMsgInfo(msg, globalTick)
            # �G�N�X�v���b�V����
            elif (msg.is_cc(CONTROL_EXPRESSION)):
                currentAddInfo.pan = MidiMsgInfo(msg, globalTick)
            # RPN MSB
            elif (msg.is_cc(CONTROL_RPN_MSB)):
                tmpRPN[0] = msg.value
            # RPN LSB
            elif (msg.is_cc(CONTROL_RPN_LSB)):
                tmpRPN[1] = msg.value
            # RPN DATA MSB�i�s�b�`�x���h�Z���V�e�B�r�e�B�j
            elif (msg.is_cc(CONTROL_RPN_DATA_MSB)):
                # �ǂ�RPN������ł��Ă���
                if ((tmpRPN[0] >= 0) and (tmpRPN[1] >= 0)):
                    # �s�b�`�x���h�Z���V�e�B�r�e�B
                    if ((tmpRPN[0] == 0) and (tmpRPN[1] == 0)):
                        currentAddInfo.pbsens = 2 #msg.value
                        if (msg.value != 2):
                            print(f"[Warning] Invalid pitch bend sensitivity: {msg.value}")
                    else:
                        print(f"[Warning] Unknown RPN: {tmpRPN[0]} {tmpRPN[1]}, Data msg: {msg}")
                else:
                    print(f"[Error] RPN Data without RPN specification: {tmpRPN[0]} {tmpRPN[1]}, Data msg: {msg}")
                    exit(1)
                # RPN�̈ꎞ�f�[�^���Z�b�g
                tmpRPN[0] = -1
                tmpRPN[1] = -1

    return noteOnInfo

# MIDI�f�[�^���󂯎��A�Z�N�V�������ƂɁA�g���b�N���m�̗ގ��x�����߂�
# ���ʂ������̔z��Ɋi�[���ĕԂ�
def CalcSimilarityBetweenTracksForEachSection(
        _midData: mido.MidiFile,
        _sectionStartBars,
        delay_max_tick: int,
        _ticksPerBar: int
):
    noteOnInfo = extractNoteOnInfo(_midData, _sectionStartBars, _ticksPerBar)
    resultDictList = []

    # �Z�N�V�������Ƃ�
    for sectionIndex in range(len(_sectionStartBars) - 1):
        # �Z�N�V�����̏����擾
        sectionEndTick = 0
        if (sectionIndex == len(_sectionStartBars) - 2): #�Ō�̃Z�N�V�����Ȃ�
            sectionEndTick = _midData.totalTicks
        else:
            sectionEndTick = (_sectionStartBars[sectionIndex + 1] - 1)*_ticksPerBar
        sectionLengthTick = sectionEndTick - (_sectionStartBars[sectionIndex] - 1)*_ticksPerBar
        sectionLengthBar = sectionLengthTick / _ticksPerBar

        # 2-2. ���������2�̃g���b�N���r
        # ��s�g���b�N�itrackX�j
        for i, trackX in enumerate(noteOnInfo[sectionIndex][1:], start=1):
            # �m�[�g�I���������g���b�N�͖���
            if (len(trackX) == 0):
                continue
            # �㑱�g���b�N�itrackY�j
            for j, trackY in enumerate(noteOnInfo[sectionIndex][1:], start=1):
                # �m�[�g�I���������g���b�N�͖���
                if (len(trackY) == 0):
                    continue
                # �����g���b�N���m�͖���
                if (i == j):
                    continue

                # �f�B���C�֌W���Z�o���邽�߂̕ϐ�
                XBase_delayRelationScore = 0 # X���猩�āAX����Y�Ƀf�B���C�֌W�����邩�������X�R�A
                YBase_delayRelationScore = 0 # Y���猩�āAX����Y�Ƀf�B���C�֌W�����邩�������X�R�A
                haveDelay = [] # �g���b�NX���ŁA�g���b�NY�Ɍ㑱���鉹�����݂��鉹���L�^����z��
                haveOriginal = [] # �g���b�NY���ŁA�g���b�NX�ɐ�s���鉹�����݂��鉹���L�^����z��
                netXNoteOnCount = getNetNoteCount(trackX) # �g���b�NX�̐����m�[�g�I����
                netYNoteOnCount = getNetNoteCount(trackY) # �g���b�NY�̐����m�[�g�I����

                # �g���b�NX���̊e�m�[�g�I���ɂ��āA
                # ���̒���ɓ��������̉����g���b�NY�Ɍ���邩�i���f�B���C�������邩�j����
                for noteOnX in trackX:
                    # �O����T��
                    for noteOnY in trackY:
                        # �^�C�~���O���f�B���C�͈͓���
                        if ((noteOnX.tick <= noteOnY.tick)
                            and (noteOnY.tick <= noteOnX.tick + delay_max_tick)):
                            # ������������
                            if (noteOnX.msg.note % 12 == noteOnY.msg.note % 12):
                                tmpNoteOn = copy.deepcopy(noteOnX)
                                tmpNoteOn.following = noteOnY
                                haveDelay.append(tmpNoteOn)

                # �g���b�NY���̊e�m�[�g�I���ɂ��āA
                # ���̒��O�ɓ��������̉����g���b�NX�Ɍ���邩�i�����������邩�j����
                for noteOnY in trackY:
                    # ��납�猟��
                    for noteOnX in reversed(trackX):
                        # �^�C�~���O���f�B���C�͈͓���
                        if ((noteOnX.tick <= noteOnY.tick)
                            and (noteOnY.tick <= noteOnX.tick + delay_max_tick)):
                            # ������������
                            if (noteOnX.msg.note % 12 == noteOnY.msg.note % 12):
                                tmpNoteOn = copy.deepcopy(noteOnY)
                                tmpNoteOn.preceding = noteOnX
                                haveOriginal.append(tmpNoteOn)
                
                # �X�R�A�Z�o
                XBase_delayRelationScore = getNetNoteCount(haveDelay) / netXNoteOnCount
                YBase_delayRelationScore = getNetNoteCount(haveOriginal) / netYNoteOnCount

                # �X�R�A�������𖞂����ꍇ�ɂ̂݋L�^
                isStrong = (XBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD)\
                            & (YBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD)
                if (XBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD):
                    # resultDictList.append(
                    #     analyzeAddData(haveDelay, XBase_delayRelationScore,\
                    #                    i, j, sectionIndex, sectionLengthBar,\
                    #                    _midData.ticks_per_beat, isStrong)
                    # )
                    for msgNum, msgInfo in enumerate(haveDelay):
                        resultDictList.append(
                            makeRecordFromMsgInfo(msgNum, msgInfo, XBase_delayRelationScore,\
                                            i, j, sectionIndex, sectionLengthBar,\
                                            _midData.ticks_per_beat, isStrong)
                        )
                if (YBase_delayRelationScore >= DELAY_RELATION_SCORE_THRESHOLD):
                    # resultDictList.append(
                    #     analyzeAddData(haveOriginal, YBase_delayRelationScore,\
                    #                    i, j, sectionIndex, sectionLengthBar,\
                    #                    _midData.ticks_per_beat, isStrong, False)
                    # )
                    for msgNum, msgInfo in enumerate(haveOriginal):
                        resultDictList.append(
                            makeRecordFromMsgInfo(msgNum, msgInfo, XBase_delayRelationScore,\
                                            i, j, sectionIndex, sectionLengthBar,\
                                            _midData.ticks_per_beat, isStrong, False)
                        )
    
    
    return resultDictList

# �ǉ����̈��S�Ȏ��o��
def _q(_instance: MidiMsgInfo, _member1: str, _member2: str, default):
    if (getattr(_instance.addInfo, _member1) is None):
        return default
    else:
        if (_member2 == ""):
            return getattr(_instance.addInfo, _member1)
        else:
            return getattr(getattr(_instance.addInfo, _member1).msg, _member2)

# �������ʂ��Z�o
def getOverallVolume(_msg: MidiMsgInfo):
    return \
    _q(_msg, "mainVol", "value", MAINVOLUME_DEFAULT)\
    * _q(_msg, "express", "value", EXPRESSION_DEFAULT)\
    * _msg.msg.velocity\
    / (127 * 127 * 127)

# 2�̉��F�������O���[�v�ɂ��邩���ׂ�
def GetDiffProgramGroup(_program1: int, _program2: int):
    if (_program1 == _program2):
        return 0
    if ((_program1 // 8) == (_program2 // 8)):
        return 1
    return 2

# MidiMsgInfo����A���R�[�h�ƂȂ鎫�����쐬����
def makeRecordFromMsgInfo(
        _msgInfoNum: int,
        _msgInfo: MidiMsgInfo, 
        _delayRelationScore: float, 
        _trackXNum: int, _trackYNum: int, 
        _sectionIndex: int, _sectionLengthBar, 
        _ticksPerBeat: int,
        _isStrong: bool,
        _isPre: bool =True
    ):
    # �K�v�ȏ�񂾂������o���Ċi�[����
    infos = {
        # ���ʃf�[�^
        "TicksPerBeat": _ticksPerBeat,
        "TrackX": _trackXNum,
        "TrackY": _trackYNum,
        "IsStrong": _isStrong,
        "Section": _sectionIndex,
        "SectionLength(Bar)": _sectionLengthBar,
        "Score": _delayRelationScore,
        "MsgNumber": _msgInfoNum,
        "GlobalTick": _msgInfo.tick,
        "NoteNumber": _msgInfo.msg.note % 12,
        # �ʃf�[�^
        "Base": "",
        "X_note": 0, #�m�[�g�ԍ�
        "X_tempo": 0, #�e���|
        "X_program": 0, #���F
        "X_pitch": 0, #�s�b�`
        "X_pan": 0, #�p��
        "X_mainVol": 0, #�剹��
        "X_expression": 0, #�G�N�X�v���b�V����
        "X_velocity": 0, #�x���V�e�B
        "X_ovVol": 0, #��������
        "Y_note": 0,
        "Y_tempo": 0,
        "Y_program": 0,
        "Y_pitch": 0,
        "Y_pan": 0,
        "Y_mainVol": 0,
        "Y_expression": 0,
        "Y_velocity": 0,
        "Y_ovVol": 0,
        # ����
        "Diff_timing": 0, #�����^�C�~���O�̍�
        "Diff_timing(MicroSeconds)": 0, #�����^�C�~���O�̍��i�����ԁj
        "Diff_program": 0, #���F�̍�
        "Diff_program(group)": 0, #���F�O���[�v�̍�
        "Diff_pitch": 0, #�s�b�`�̍�
        "Diff_pan": 0, #�p���̍�
        "Diff_mainVol": 0, #�剹�ʂ̍�
        "Diff_expression": 0, #�G�N�X�v���b�V�����̍�
        "Diff_velocity": 0, #�x���V�e�B�̍�
        "Diff_ovVol": 0, #�������ʂ̍�
        "Diff_octave": 0 #�I�N�^�[�u�̍�
    }

    if (_isPre):
        infos["Base"] = "X"
        infos["X_note"] = _msgInfo.msg.note
        infos["X_tempo"] = _q(_msgInfo, "tempo", "tempo", PROGRAM_DEFAULT)
        infos["X_program"] = _q(_msgInfo, "program", "program", PROGRAM_DEFAULT)
        infos["X_pitch"] =\
            _q(_msgInfo, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo, "pbsens", "", PBSENS_DEFAULT)
        infos["X_pan"] = _q(_msgInfo, "pan", "value", PAN_DEFAULT)
        infos["X_mainVol"] = _q(_msgInfo, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["X_expression"] = _q(_msgInfo, "express", "value", EXPRESSION_DEFAULT)
        infos["X_velocity"] = _msgInfo.msg.velocity
        infos["X_ovVol"] = getOverallVolume(_msgInfo)
        
        infos["Y_note"] = _msgInfo.following.msg.note
        infos["Y_tempo"] = _q(_msgInfo.following, "tempo", "tempo", TEMPO_DEFAULT)
        infos["Y_program"] = _q(_msgInfo.following, "program", "program", PROGRAM_DEFAULT)
        infos["Y_pitch"] =\
            _q(_msgInfo.following, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo.following, "pbsens", "", PBSENS_DEFAULT)
        infos["Y_pan"] = _q(_msgInfo.following, "pan", "value", PAN_DEFAULT)
        infos["Y_mainVol"] = _q(_msgInfo.following, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["Y_expression"] = _q(_msgInfo.following, "express", "value", EXPRESSION_DEFAULT)
        infos["Y_velocity"] = _msgInfo.following.msg.velocity
        infos["Y_ovVol"] = getOverallVolume(_msgInfo.following)
        
        infos["Diff_timing"] = _msgInfo.following.tick - _msgInfo.tick
        infos["Diff_timing(MicroSeconds)"] =\
            infos["Diff_timing"] * infos["X_tempo"] / infos["TicksPerBeat"]
        infos["Diff_program"] = infos["Y_program"] - infos["X_program"]
        infos["Diff_program(group)"] = GetDiffProgramGroup(infos["X_program"], infos["Y_program"])
        infos["Diff_pitch"] = infos["Y_pitch"] - infos["X_pitch"]
        infos["Diff_pan"] = infos["Y_pan"] - infos["X_pan"]
        infos["Diff_mainVol"] = infos["Y_mainVol"] - infos["X_mainVol"]
        infos["Diff_expression"] = infos["Y_expression"] - infos["X_expression"]
        infos["Diff_velocity"] = infos["Y_velocity"] - infos["X_velocity"]
        infos["Diff_ovVol"] = infos["Y_ovVol"] - infos["X_ovVol"]
        infos["Diff_octave"] = (_msgInfo.following.msg.note - _msgInfo.msg.note) / 12
    else:
        infos["Base"] = "Y"
        infos["Y_note"] = _msgInfo.msg.note
        infos["Y_tempo"] = _q(_msgInfo, "tempo", "tempo", PROGRAM_DEFAULT)
        infos["Y_program"] = _q(_msgInfo, "program", "program", PROGRAM_DEFAULT)
        infos["Y_pitch"] =\
            _q(_msgInfo, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo, "pbsens", "", PBSENS_DEFAULT)
        infos["Y_pan"] = _q(_msgInfo, "pan", "value", PAN_DEFAULT)
        infos["Y_mainVol"] = _q(_msgInfo, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["Y_expression"] = _q(_msgInfo, "express", "value", EXPRESSION_DEFAULT)
        infos["Y_velocity"] = _msgInfo.msg.velocity
        infos["Y_ovVol"] = getOverallVolume(_msgInfo)

        infos["X_note"] = _msgInfo.preceding.msg.note
        infos["X_tempo"] = _q(_msgInfo.preceding, "tempo", "tempo", TEMPO_DEFAULT)
        infos["X_program"] = _q(_msgInfo.preceding, "program", "program", PROGRAM_DEFAULT)
        infos["X_pitch"] =\
            _q(_msgInfo.preceding, "pitch", "pitch", PITCH_DEFAULT)\
            * _q(_msgInfo.preceding, "pbsens", "", PBSENS_DEFAULT)
        infos["X_pan"] = _q(_msgInfo.preceding, "pan", "value", PAN_DEFAULT)
        infos["X_mainVol"] = _q(_msgInfo.preceding, "mainVol", "value", MAINVOLUME_DEFAULT)
        infos["X_expression"] = _q(_msgInfo.preceding, "express", "value", EXPRESSION_DEFAULT)
        infos["X_velocity"] = _msgInfo.preceding.msg.velocity
        infos["X_ovVol"] = getOverallVolume(_msgInfo.preceding)
        
        infos["Diff_timing"] = _msgInfo.tick - _msgInfo.preceding.tick
        infos["Diff_timing(MicroSeconds)"] =\
            infos["Diff_timing"] * infos["X_tempo"] / infos["TicksPerBeat"]
        infos["Diff_program"] = infos["Y_program"] - infos["X_program"]
        infos["Diff_program(group)"] = GetDiffProgramGroup(infos["Y_program"], infos["X_program"])
        infos["Diff_pitch"] = infos["Y_pitch"] - infos["X_pitch"]
        infos["Diff_pan"] = infos["Y_pan"] - infos["X_pan"]
        infos["Diff_mainVol"] = infos["Y_mainVol"] - infos["X_mainVol"]
        infos["Diff_expression"] = infos["Y_expression"] - infos["X_expression"]
        infos["Diff_velocity"] = infos["Y_velocity"] - infos["X_velocity"]
        infos["Diff_ovVol"] = infos["Y_ovVol"] - infos["X_ovVol"]
        infos["Diff_octave"] = (_msgInfo.msg.note - _msgInfo.preceding.msg.note) / 12

    return infos


#================
# ���͊֐��i�S�́j
#================
# �����A�t�@�C�����A�ϊ����ꂽ���̂��ǂ����A�Ƃ�����񂩂�A�N�Z�X�ɕK�v�ȑ��΃p�X�����߂�
def getMidifilePath(_issueNum: int, _filename: str, _converted: bool =True):
    relativePath = f"../data/{_issueNum}/"
    if _converted:
        relativePath += "conv/"
    relativePath += _filename

    return relativePath

# �w�肳�ꂽ�t�@�C���𕪐͂���
def analyzeSingleMidifile(_issueNum: int, _filename: str, _converted: bool =True):
    # ================
    # �f�[�^�ǂݍ���
    # ================
    # SMF�P�̓ǂݍ���
    midData = mido.MidiFile(getMidifilePath(_issueNum, _filename, _converted))
    # �Ȗ��\��
    print(f"File: {midData.filename}, Sequence Name: {getSequenceName(midData)}")
    # �t�H�[�}�b�g1�Ȃ�A��������0�ɕϊ�
    if (midData.type == 1):
        midData = SMF1to0(midData)
    # �t�H�[�}�b�g1�ɕϊ��A��Tick�����擾
    midData = SMF0to1AndGetTotalTicks(midData)

    # ================
    # ����
    # ================
    # 1. �v���O�����`�F���W�ŃZ�N�V��������؂�
    # ���^���b�Z�[�W���甏�q���擾
    (timeSigNume, timeSigDeno) = getTimeSignature(midData)
    #print(f"- Time Signature: {timeSigNume} / {timeSigDeno}")
    # 1���߂���Tick�����߂�
    ticksPerBar = midData.ticks_per_beat * (4/timeSigDeno) * timeSigNume
    # �萔�����ƂɁA���͂ɕK�v�ȋ�̓I�Ȓl�����߂�
    delay_max_tick = midData.ticks_per_beat * DELAY_MAX_BEAT
    # �Z�N�V�����J�n���߂��i�[����z��
    # �z��̓��̐���n�́An���ߖڂ̎n�܂���Ӗ�����in=1~�j
    # �֋X��A������int�̍ő�l��ǉ�
    sectionStartBars = getSectionStartBars(midData, ticksPerBar)
    #print(f"Sections: {sectionStartBars}")

    # 2. �Z�N�V�������ƂɁA�g���b�N���m�̗ގ��x�����߂�B
    return CalcSimilarityBetweenTracksForEachSection(midData, sectionStartBars, delay_max_tick, ticksPerBar)

# �����Ώۂ̃t�@�C�������ׂĕ��͂���
def analyzeAllMidifiles(_isDebug: bool =False):
    # �������ʂ��i�[���鎫��
    survayResult = {}
    # ���������t�@�C�����i�[���郊�X�g�ƁA�t�@�C���̃n�b�V�����i�[���郊�X�g
    fileList = []
    fileHashList = []

    # SMF����
    for issueNum in range(ISSUE_MIN, ISSUE_MAX+1):
        # �ϊ�����Ă��Ȃ�SMF
        dirPath = getMidifilePath(issueNum, "", False)
        print(dirPath)
        for filename in os.listdir(dirPath):
            filePath = os.path.join(dirPath, filename)
            if (os.path.isfile(filePath)
                and os.path.splitext(filename)[1].lower() == ".mid"):
                # �d���t�@�C��������
                fileHash = ""
                with open(filePath, mode="rb") as f:
                    fileHash = sha256(f.read()).hexdigest()
                if (fileHash in fileHashList):
                    print(f"[Info] Same file exists: {filename} = {fileList[fileHashList.index(fileHash)]}")
                    continue
                # ���o�t�@�C���Ȃ�A���X�g�ɒǉ����A����
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    survayResult[filePath] = analyzeSingleMidifile(issueNum, filename, False)
        # �ϊ����ꂽSMF
        dirPath = getMidifilePath(issueNum, "", True)
        for filename in os.listdir(dirPath):
            filePath = os.path.join(dirPath, filename)
            if (os.path.isfile(filePath)
                and os.path.splitext(filename)[1].lower() == ".mid"):
                # �d���t�@�C��������
                fileHash = ""
                with open(filePath, mode="rb") as f:
                    fileHash = sha256(f.read()).hexdigest()
                if (fileHash in fileHashList):
                    print(f"[Info] Same file exists: {filename} = {fileList[fileHashList.index(fileHash)]}")
                    continue
                # ���o�t�@�C���Ȃ�A���X�g�ɒǉ����A����
                else:
                    fileList.append(filePath)
                    fileHashList.append(fileHash)
                    survayResult[filePath] = analyzeSingleMidifile(issueNum, filename, True)
        if (_isDebug):
            break
    return survayResult

# �������ʂ������o��
def outputResult(result, csvFilename: str):
    # ��؂蕶��
    sep = ";"
    # ��
    outputText = "File"
    for filePath in result.keys():
        for record in result[filePath]:
            for recordKey in record.keys():
                outputText += f"{sep}{recordKey}"
            break
        break
    outputText += "\n"
    
    # ���f�[�^
    for filePath in result.keys():
        for record in result[filePath]:
            outputText += filePath
            for recordKey in record.keys():
                outputText += f"{sep}{record[recordKey]}"
            outputText += "\n"
    
    with open(csvFilename, mode="w") as f:
        f.write(outputText)


# ================
# ���C������
# ================
# �������ʂ��i�[���鎫���쐬
result = analyzeAllMidifiles(False)

# �������ʂ������o��
outputResult(result, "out.csv")
