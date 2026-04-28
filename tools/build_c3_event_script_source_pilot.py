from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decode_event_script import CALL_ARG_COUNTS, OPCODES, Address, Opcode, load_names, read_u16
from rom_tools import find_rom, hirom_to_file_offset, load_rom


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MAP = ROOT / "build" / "c3-source-data-map.json"
DEFAULT_REF_INDEX = ROOT / "build" / "ref-index.json"
DEFAULT_OUTPUT = ROOT / "src" / "c3" / "event_scripts" / "movement_pulse_presets.asar.asm"
DEFAULT_REPORT = ROOT / "notes" / "c3-event-script-source-pilot.md"
DEFAULT_MANIFEST = ROOT / "build" / "c3-event-script-source-pilot.json"

FAMILY_ID = "movement-pulse-presets"

SCRIPT_ROWS = [
    "C3:A09F",
    "C3:A0B2",
    "C3:A0C5",
    "C3:A0D8",
    "C3:A12E",
    "C3:A15E",
    "C3:A17B",
    "C3:A18F",
    "C3:A1A3",
    "C3:A1B7",
    "C3:A1CB",
    "C3:A1DF",
    "C3:A1F3",
]

PRESET_ROWS = [
    "C3:AA38",
    "C3:AA46",
    "C3:AA5A",
    "C3:AA6E",
    "C3:AA82",
    "C3:AA96",
    "C3:AAAA",
    "C3:AAB8",
    "C3:AAC2",
    "C3:AAD6",
    "C3:AAEA",
    "C3:AAFE",
    "C3:AB12",
    "C3:AB26",
]

LABEL_OVERRIDES = {
    "C3:43DB": "LoopTimedDeliveryDeparturePulseUntilOffscreen",
    "C3:43E8": "TimedDeliveryDeparturePulseAnimation0Half",
    "C3:4402": "Event500_TimedDeliveryExistingRowGate",
    "C3:441A": "Event499_TimedDeliverySetup",
    "C3:4432": "TimedDeliveryCommonCountdownLoop",
    "C3:443E": "TimedDeliveryRetryWaitLoop",
    "C3:444D": "TimedDeliveryReadinessGate",
    "C3:4457": "TimedDeliverySuccessGateAndPresentationSetup",
    "C3:447A": "StartTimedDeliveryArrivalMovementTask",
    "C3:447D": "TimedDeliveryFailureTeardown",
    "C3:4488": "PrepareTimedDeliveryActorForPresentation",
    "C3:4499": "WaitTimedDeliveryActorPresentationPrep",
    "C3:44A7": "ReturnFromTimedDeliveryActorPrep",
    "C3:44A8": "RunTimedDeliveryDepartureMovement",
    "C3:44C1": "LoopTimedDeliveryDepartureMovement",
    "C3:44D2": "FinishTimedDeliveryDepartureAndYieldText",
    "C3:44DE": "RunTimedDeliveryArrivalMovement",
    "C3:44EE": "LoopTimedDeliveryArrivalMovement",
    "C3:44FF": "HoldTimedDeliveryArrivalCompletion",
    "C3:4508": "Event547_CameraOffsetPulseAndYield",
    "C3:4555": "Event547_VerticalCameraOffsetPulseTask",
    "C3:456F": "Event550_ReleaseCurrentVisualEntity",
    "C3:4572": "Event548_FourDirectionIdlePresentation",
    "C3:459E": "Event549_DownwardMovementToYield",
    "C3:45CA": "Event551_ServiceMovementPath",
    "C3:4635": "Event552_ServiceMovementPath",
    "C3:4693": "Event553_ServiceMovementPath",
    "C3:46F1": "Event554_ServiceMovementPathAndFade",
    "C3:474E": "Event555_BrightnessFadeOut",
    "C3:4767": "Event559_ServiceMovementPath",
    "C3:47C1": "Event558_ServiceMovementPath",
    "C3:4810": "Event557_ServiceMovementPath",
    "C3:486A": "Event556_ServiceMovementPath",
    "C3:48C4": "PlayDownRightLeftDownFacingGesture",
    "C3:48FC": "Event563_FacingCountdownSequence",
    "C3:4964": "LoopReadScriptWords0201Task",
    "C3:4975": "Event562_ServiceAnimationWithReadTask",
    "C3:4A61": "LoopReadScriptWord01Task",
    "C3:4A55": "WaitUntilCurrentSlotInsideLiveAreaWindow",
    "C3:4A6C": "Event561_ServiceAnimationWithReadTask",
    "C3:4AF6": "Event560_ServiceFacingSequence",
    "C3:4B62": "PlayDirectionCountdownCompassCycle",
    "C3:4BAB": "Event564_StaticFacingPresentationRelease",
    "C3:4BCD": "Event565_RightThenUpFacingHalt",
    "C3:4BF7": "Event566_MoveThenFaceUpHalt",
    "C3:4C3A": "Event567_MoveToFixedAnchorPartyLookAt",
    "C3:4C86": "Event568_MoveFromPartyMemberLeftToAnchor",
    "C3:4CE0": "Event569_MoveFromPartyMemberRightToAnchor",
    "C3:4D39": "RunFallingBouncePresentation",
    "C3:4D5C": "Event570_FallingBouncePositionA",
    "C3:4D65": "Event571_FallingBouncePositionB",
    "C3:4D6E": "Event572_FallingBouncePositionC",
    "C3:4D77": "Event573_HoldFacingPositionA",
    "C3:4D7D": "HoldDownFacingTwoSecondsAndRelease",
    "C3:4D92": "Event574_HoldFacingPositionB",
    "C3:4D9B": "Event575_HoldFacingPositionC",
    "C3:4DA4": "Event576_ReleaseCurrentVisualEntity",
    "C3:4DA7": "Event577_TrafficLightWaitPositionA",
    "C3:4DB0": "Event578_TrafficLightWaitPositionB",
    "C3:4DB9": "Event579_TrafficLightWaitPositionC",
    "C3:4DC2": "Event580_TrafficLightWaitPositionD",
    "C3:4DCB": "Event581_DoseiBoxAppearFlagGate",
    "C3:4DE0": "Event582_DownFacingWindowEffect",
    "C3:4DEA": "Event583_UpFacingWindowEffect",
    "C3:4DF1": "RunWh0ColorWindowRiseAndFallEffect",
    "C3:4E66": "LoopMovementVectorFromDirectionTask",
    "C3:4E73": "InitSimpleScreenPositionIntroActor",
    "C3:4E85": "Event535_ItoiProductionIntroTextPath",
    "C3:4EC8": "Event536_ItoiProductionLoopWalkPath",
    "C3:4F31": "Event537_ItoiProductionRafflesiaPath",
    "C3:4F7E": "WaitUntilTempFlag1Clear",
    "C3:4F9B": "Event538_SetTempFlag1AfterShortMove",
    "C3:4FC7": "Event539_ItoiSimpleScreenPositionPath",
    "C3:4FF8": "Event540_FixedRightFacingHalt",
    "C3:500E": "Event541_IntroMovementWithLeftFacingTask",
    "C3:504A": "LoopForceLeftFacingTask",
    "C3:5056": "Event542_LongLeftFacingMovementPath",
    "C3:50B0": "Event543_DownFacingDropAndHoldPath",
    "C3:50F4": "Event544_FoursideSpectatorTextPath",
    "C3:5154": "Event545_RightFacingMovementPath",
    "C3:5198": "Event546_NintendoPresentationIntroPath",
    "C3:51FD": "Event799_ObscuredDownFacingCastActorHalt",
    "C3:5214": "Event800_ObscuredDownFacingCastActorRefreshGate",
    "C3:5226": "LoopWaitForCastActorRefreshFlag",
    "C3:1D2D": "LoopVar4TimedAnimationPulse",
    "C3:1D4A": "PauseThenRestartVar4AnimationPulse",
    "C3:1D4F": "InitVar4TimedAnimationPulseMovement",
    "C3:1EC1": "RunRightwardStepPulseHelper",
    "C3:1ED8": "RunLeftwardStepPulseHelper",
    "C3:2CD2": "LoopStageActorVerticalBounce",
    "C3:2CF0": "Event399_TStagePerformanceMovementRelease",
    "C3:3399": "PulseDownFacingVisualCountdown",
    "C3:33AA": "PulseUpFacingVisualCountdown",
    "C3:33BB": "PulseLeftFacingVisualCountdown",
    "C3:33CC": "PulseRightFacingVisualCountdown",
    "C3:33DD": "RunStageFacingVisualPulsePattern",
    "C3:3424": "Event435_StagePerformancePulseRelease",
    "C3:34CF": "Event436_ObscuredStageSlideRelease",
    "C3:3BFB": "RunWindowGfxVariantLoaderPrologue",
    "C3:3C08": "LoopWindowGfxVariantLoader",
    "C3:3C18": "UndrawFlyoverTextAndReturn",
    "C3:3C1D": "RunWindowGfxVariantLoop",
    "C3:3C2F": "ReturnFromWindowGfxVariantLoop",
    "C3:3C30": "Event467_RandomFacingIdleLoop",
    "C3:3C3E": "LoopEvent467_RandomFacingIdle",
    "C3:3C6C": "Event465_PartyLookMovementPath",
    "C3:3CDA": "Event466_PartyLookLoopingMovementPath",
    "C3:3D30": "LoopEvent466_RectanglePath",
    "C3:3DBE": "LoopEvent465_466Field2B32PulseTask",
    "C3:4392": "RunLeftwardBoundsReleasePath",
    "C3:43AE": "LoopWatchBoundsForLeftwardRelease",
    "C3:43C4": "CheckUpperBoundForLeftwardRelease",
    "C3:43D8": "ReleaseAfterLeftwardBoundsSatisfied",
    "C3:5F8B": "LoopCastScreenActorRefreshGateTask",
    "C3:5F98": "CheckCastScreenActorStillVisible",
    "C3:5FAC": "CheckCastScreenActorLoopContinuation",
    "C3:5FB3": "ReleaseCastScreenActorAndEnd",
    "C3:5FB6": "InitFlatCastScreenActorWithRefreshTask",
    "C3:5FCD": "InitDepthCastScreenActorWithRefreshTask",
    "C3:5FE2": "Event802_CastDownFacingHalt",
    "C3:5FF1": "Event803_CastUpFacingHalt",
    "C3:6000": "Event809_CastDownFacingWalkoffGesture",
    "C3:6073": "Event810_CastDownLeftIdleLoop",
    "C3:6076": "LoopEvent810_CastDownLeftIdle",
    "C3:6093": "Event811_CastDownRightIdleLoop",
    "C3:6096": "LoopEvent811_CastDownRightIdle",
    "C3:60B3": "Event812_CastDownLeftExitGesture",
    "C3:60EC": "Event813_CastDownRightDownVisualCountdown",
    "C3:610A": "Event814_CastUpThenLeftDownHalt",
    "C3:6144": "Event815_CastRightMoveRelease",
    "C3:6169": "Event816_CastDownRightLeftRelease",
    "C3:61AA": "Event817_CastPriority3DownHalt",
    "C3:61BB": "Event818_CastPriority0DownHalt",
    "C3:61CC": "Event819_DepthCastDownFacingHalt",
    "C3:61DB": "Event820_CastRightThenUpHalt",
    "C3:61FB": "Event821_CastDownThenUpHalt",
    "C3:6219": "Event822_CastLeftThenUpHalt",
    "C3:6239": "Event823_CastPauseRightThenDownHalt",
    "C3:626E": "Event824_CastDownUpThenDownHalt",
    "C3:629F": "Event825_CastBrokenPhaseDistorterSpawn",
    "C3:6834": "SpawnKingThenReleaseCurrentVisualEntity",
    "C3:683F": "Event845_DownFacingShortWaitSpawnRelease",
    "C3:6852": "Event846_DownFacingMediumWaitSpawnRelease",
    "C3:6867": "Event847_DownFacingLongWaitSpawnRelease",
    "C3:687C": "Event848_DownFacingOffsetWaitSpawnRelease",
    "C3:6891": "Event849_DownFacingLongOffsetWaitSpawnRelease",
    "C3:68A6": "Event850_LeftStepThenDownFacingHalt",
    "C3:68CF": "Event851_RightStepThenDownFacingHalt",
    "C3:68F8": "Event852_CastScreenFacingCycleUntilInvisible",
    "C3:690F": "LoopEvent852_CastScreenFacingCycle",
    "C3:699B": "Event853_LeftFacingPauseSpawnKing",
    "C3:69AF": "SpawnEvent854KingThenReleaseCurrentVisualEntity",
    "C3:69BA": "Event854_LeftFacingHalt",
    "C3:69C9": "Event855_RightStepThenDownFacingHalt",
    "C3:69E2": "Event856_LeftStepThenDownFacingHalt",
    "C3:69FB": "Event857_DownFacingPauseSpawnNessPosing",
    "C3:6A1F": "SpawnEvent858NessPosingThenReleaseCurrentVisualEntity",
    "C3:6A2A": "Event858_DownFacingProjectedPoseHalt",
    "C3:6A3E": "ReleaseCurrentVisualEntityFromCastPath",
    "C3:6A41": "PrepareObscuredVehiclePathActor",
    "C3:6A53": "Event584_OnettTaxiLoopUntilDoorClose",
    "C3:6A69": "LoopEvent584_OnettTaxiPatrol",
    "C3:6A98": "Event585_OnettTruck2ParkAfterDoorClose",
    "C3:6ABF": "Event586_OnettTruck1ParkAfterDoorClose",
    "C3:6AE6": "Event587_UnplacedVehicleStop",
    "C3:6AFF": "Event588_TwosonRedCarStop",
    "C3:6B18": "Event589_TwosonTruck2TwoStopPath",
    "C3:6B4B": "Event590_TwosonTaxiBusAppearGate",
    "C3:6B60": "RunTwosonTaxiBusAppearPath",
    "C3:6BB4": "LoopVar3VerticalBounce",
    "C3:6BC1": "LoopVar3VerticalBouncePauseOnly",
    "C3:6BC6": "Event591_ThreedFightMatentTextHalt",
    "C3:6BEA": "EndBeforeBoogyTentEyeLiveAreaGate",
    "C3:6BEB": "Event592_BoogyTentEyeLiveAreaGate",
    "C3:6BF4": "LoopEvent592_WaitUntilInsideLiveArea",
    "C3:6C00": "Event593_Set1510_2588MoveDownLeftRelease",
    "C3:6C4A": "Event594_Set1530_2588MoveDownRightRelease",
    "C3:6C94": "Event595_CityBusCoordinatePath",
    "C3:6CDB": "Event596_BounceYieldRelease",
    "C3:6CEC": "LoopEvent596_ZBounce",
    "C3:098B": "WaitMovementThenYieldHalt",
    "C3:0993": "Event266_MoveTo01F0_08E8YieldHalt",
    "C3:0C55": "InitMovementPresetField2B32AndRefreshVisual",
    "C3:0C67": "LoopLongCoordinatePatrolRoute",
    "C3:0C7F": "LongCoordinatePatrolRoutePhaseB",
    "C3:0C97": "LongCoordinatePatrolRoutePhaseC",
    "C3:0CAF": "LongCoordinatePatrolRoutePhaseD",
    "C3:0CC7": "LongCoordinatePatrolRoutePhaseE",
    "C3:0CE2": "Event284_BubbleMonkeyByeMovementRelease",
    "C3:0D1E": "Event285_BubbleMonkeyMovementTextRelease",
    "C3:0D3C": "RunBubbleMonkeyLongCoordinateRoute",
    "C3:0DB6": "Event286_GiygasWinFlagWaitRelease",
    "C3:09B0": "Event267_FallingBounceRelease",
    "C3:09D0": "LoopEvent267_WaitForMovementWrapper",
    "C3:0A1F": "ShortZBounceTask",
    "C3:0A32": "Event268_FixedCoordinateJumpRelease",
    "C3:0A76": "Event269_FixedCoordinateRelease",
    "C3:0A91": "Event270_PokeyVisualTargetTextPath",
    "C3:0ACB": "Event271_PokeyVisualTargetShakePath",
    "C3:0AF8": "Event272_PokeyRattleAndRisePath",
    "C3:0B4E": "Event273_PokeyBattleStagingPath",
    "C3:0BEA": "Event274_275_276_PartyMemberMovementHalt",
    "C3:0C09": "Event277_LeftMovementTextHalt",
    "C3:0C20": "Event278_RightMovementTextHalt",
    "C3:0C37": "Event279_BubbleMonkeyRouteStartA",
    "C3:0C3D": "Event280_BubbleMonkeyRouteStartB",
    "C3:0C43": "Event281_BubbleMonkeyRouteStartC",
    "C3:0C49": "Event282_BubbleMonkeyRouteStartD",
    "C3:0C4F": "Event283_BubbleMonkeyRouteStartE",
    "C3:6E2D": "Event606_DoseiBoxAppearFallback",
    "C3:7439": "PrepareAlignedMovementToY1616",
    "C3:7456": "Event633_PaletteFadeYieldFast",
    "C3:7464": "LoopEvent633_PaletteFade",
    "C3:7479": "Event634_PaletteFadeYieldSlow",
    "C3:7487": "LoopEvent634_PaletteFade",
    "C3:749C": "Event635_BlinkThreeTimesRelease",
    "C3:74A2": "LoopEvent635_Blink",
    "C3:74B0": "Event636_CoordinateSoundYieldHalt",
    "C3:74E4": "Event637_CoordinateTextYieldRelease",
    "C3:7511": "Event637_StartFastPulseFinalMove",
    "C3:7530": "Event637_StartTwoFramePulseFinalMove",
    "C3:7545": "RunRightLeftFacingPulsePair",
    "C3:7559": "RunLeftRightFacingPulsePair",
    "C3:83BC": "ChooseRandomFacingCycleStepCount",
    "C3:83D2": "Event693_LiveAreaFacingCycleFast",
    "C3:83E0": "LoopEvent693_LiveAreaFacingCycleFast",
    "C3:840A": "Event694_LiveAreaFacingCycleSlow",
    "C3:8418": "LoopEvent694_LiveAreaFacingCycleSlow",
    "C3:8442": "Event695_LongMovementPathYield",
    "C3:84D8": "Event688_TargetMovementAnchorA",
    "C3:84E3": "Event689_TargetMovementAnchorB",
    "C3:84EE": "Event690_TargetMovementAnchorC",
    "C3:84F9": "RunTargetMovementAnchorPath",
    "C3:835D": "SwitchAnimPortFlagsFromTempvar",
    "C3:8370": "SetAnimPortFlags00",
    "C3:8383": "SetAnimPortFlags01",
    "C3:8396": "SetAnimPortFlags10",
    "C3:83A9": "SetAnimPortFlags11",
    "C3:8978": "LoopAnimPortDirectionFromVar4",
    "C3:898C": "UseDirectionRightWhenAnimPort0Clear",
    "C3:8992": "UseDirectionDownWhenVar4Clear",
    "C3:8995": "ApplyAnimPortDirectionAndLoop",
    "C3:899E": "LoopAnimPortBlinkAnimation",
    "C3:89BD": "Event715_BlinkThenRelease",
    "C3:89DD": "Event716_OffsetPoseHalt",
    "C3:89FB": "Event717_OnettTownHallLongMovementPath",
    "C3:8A3D": "RunEvent717_LeftRightFacingPulse",
    "C3:8AB1": "Event718_OnettTownHallShortMovementHalt",
    "C3:8ADC": "Event719_OnettTownHallDoorMovementPath",
    "C3:8B29": "LoopEvent719_DoorSoundTask",
    "C3:8B3A": "Event720_MovementPathRelease",
    "C3:8B5D": "Event721_MovementPathEndTaskHalt",
    "C3:8B7F": "Event722_DoorwayMovementPath",
    "C3:8BC5": "Event723_DoorwayMovementTextYield",
    "C3:8BFC": "Event724_DoorOpenCloseMovementPath",
    "C3:8C7C": "Event725_DoorCloseMovementPath",
    "C3:8CB0": "Event726_DoorCloseShortMovementPath",
    "C3:8CE4": "Event727_DoorCloseAlignedMovementPath",
    "C3:8D18": "Event728_DoorCloseTextYieldMovementPath",
    "C3:8D50": "Event729_TownHallDoorSoundMovementPath",
    "C3:8DB3": "Event730_DirectionTrackerTask",
    "C3:8DBD": "LoopEvent730_DirectionTrackerTask",
    "C3:8DD8": "Event731_DirectionTrackerMovementPath",
    "C3:8DFC": "Event732_DirectionTrackerMovementPath",
    "C3:8E32": "Event733_DirectionTrackerMovementPath",
    "C3:8E61": "Event734_DirectionTrackerTextYieldPath",
    "C3:8E89": "Event735_SoundMovementTextHalt",
    "C3:8EB9": "Event736_RandomFacingTextHalt",
    "C3:8EEA": "Event737_SetDownDirectionAndJumpCommon",
    "C3:8F06": "Event737_740_CommonDirectionHalt",
    "C3:9E01": "WaitUntilNoBattleSwirlOrEnemyTouch",
    "C3:A2B8": "Event8_Entry2WaitUntilOffscreenRelease",
    "C3:A09F": "LoopActiveEntityWalkAnimationPulse",
    "C3:A0B2": "LoopActiveEntityWalkPulse24Frame",
    "C3:A0C5": "LoopActiveEntityWalkPulse12Frame",
    "C3:A0D8": "LoopActiveEntityWalkPulse9FrameConditional",
    "C3:A0EB": "LoopActiveEntityWalkPulse6FrameConditional",
    "C3:A0FE": "LoopActiveEntityWalkPulse2FrameConditional",
    "C3:A111": "LoopActiveEntityWalkPulseVar4Gate",
    "C3:A11E": "LoopActiveEntityWalkPulseVar4Gate_OffHalf",
    "C3:A12E": "LoopActiveEntityWalkPulseVar4Countdown",
    "C3:A159": "LoopActiveEntityWalkPulseVar4Countdown_WaitAndRestart",
    "C3:A15E": "LoopC40015Var4GatedPulseUntilRelease",
    "C3:A162": "LoopC40015Var4GatedPulseUntilRelease_Loop",
    "C3:A16F": "LoopC40015Var4GatedPulseUntilRelease_CheckRelease",
    "C3:A17B": "LoopC40015SlowPulseUntilRelease",
    "C3:A18F": "LoopC40015FastPulseUntilRelease",
    "C3:A1A3": "LoopC40015Pulse12FrameUntilRelease",
    "C3:A1B7": "LoopC40015Pulse9FrameUntilRelease",
    "C3:A1CB": "LoopC40015Pulse6FrameUntilRelease",
    "C3:A1DF": "LoopActiveEntityWalkPulse2FrameC40015Branch",
    "C3:A1F3": "LoopC40015Pulse16FrameUntilRelease",
    "C3:A204": "ReleaseCurrentVisualEntityAndEnd",
    "C3:A209": "DelayThenReleaseCurrentVisualEntity",
    "C3:A20E": "LoopVar0SelectedAnimationUntilOffscreen",
    "C3:A214": "LoopVar0SelectedAnimationBody",
    "C3:A22C": "Var0AnimationCase0Pulse8FrameOn",
    "C3:A234": "Var0AnimationCase1Pulse8FrameOff",
    "C3:A23D": "Var0AnimationCase2Pulse4Frame",
    "C3:A24E": "Var0AnimationCase3Pulse32Frame",
    "C3:A25F": "Var0AnimationCase4Wait16Frame",
    "C3:A262": "LoopActiveEntityCollisionProbeRefresh",
    "C3:A266": "LoopCollisionProbeRefresh",
    "C3:A271": "EndCurrentEventTask",
    "C3:A47C": "ReleaseCurrentVisualEntityTail",
    "C3:AA38": "InitActionScriptMovementState",
    "C3:AA46": "InitMovementPreset40_00Pulse24Frame",
    "C3:AA5A": "InitMovementPreset00_01Pulse12Frame",
    "C3:AA6E": "InitMovementPreset60_01Pulse9Frame",
    "C3:AA82": "InitMovementPreset00_02Pulse6Frame",
    "C3:AA96": "InitMovementPreset00_06Pulse2Frame",
    "C3:AAAA": "InitMovementPresetVar4Countdown",
    "C3:AAB8": "InitMovementPresetC40015Pulse16Frame",
    "C3:AAC2": "InitMovementPreset40_00C40015FastPulse",
    "C3:AAD6": "InitMovementPreset00_01C40015Pulse12Frame",
    "C3:AAEA": "InitMovementPreset60_01C40015Pulse9Frame",
    "C3:AAFE": "InitMovementPreset00_02C40015Pulse6Frame",
    "C3:AB12": "InitMovementPreset00_06C40015Branch",
    "C3:AB26": "InitAlternatePhysicsVar4WalkPulse",
    "C3:AA1E": "ApplyTempDirectionAndRefreshMovementVector",
    "C3:AA2B": "InitMovementWithDefaultPhysicsPulseAndCollisionProbe",
    "C3:AB37": "InitSimpleScreenPositionMovementCallbacks",
    "C3:AB44": "RefreshActiveEntityDirectionAndVisualProfile",
    "C3:AB59": "WaitForActiveEntityMovementToFinish",
    "C3:AB5C": "LoopWaitForActiveEntityMovementToFinish",
    "C3:AB67": "MoveCurrentSlotAwayFromTargetVector",
    "C3:AB7F": "LoopMoveCurrentSlotAwayFromTargetVector",
    "C3:AB8A": "WaitUntilPlayerLeavesActiveArea",
    "C3:AB94": "WaitUntilPlayerEntersActiveArea",
    "C3:AB9E": "LoopRandomWanderInsideActiveArea",
    "C3:ABAC": "ChooseRandomCardinalDirection",
    "C3:ABB9": "ApplyRandomWanderDirectionAndTimer",
    "C3:ABCF": "ChooseRandomWanderWaitTimer",
    "C3:ABE0": "WaitUntilWram0028LowByteSet",
    "C3:AFA3": "LoopPartyLooksAtActiveEntity",
    "C3:B70C": "RunFaceTargetShakeByRegistryCount",
    "C3:B737": "LoopWaitForFaceTargetShakeGate",
    "C3:B757": "Event73_TargetPoseApproachShakeAndYield",
    "C3:B784": "Event74_DownRightWalkAndYield",
    "C3:B7BC": "Event75_PartyLookAtMemberOffsetAndYield",
    "C3:B7EF": "Event76_C40015PresetMoveToPoseAndYield",
    "C3:B810": "Event77_BikiniZombieNearTextPath",
    "C3:B86C": "Event78_BikiniZombieFlaggedLeftMove",
    "C3:B8A5": "Event79_BikiniZombieHotelDoorPath",
    "C3:B8E8": "Event80_ResetVar4AfterPartyMove",
    "C3:B902": "Event81_PartyLookTaskUnknown61Release",
    "C3:B926": "Event82_DirectionalUnknown61Release",
    "C3:B95D": "Event83_PartyMemberOneOuchSequence",
    "C3:B9B6": "Event84_PartyMemberOneYieldAndHold",
    "C3:B9D4": "Event85_TwosonThreedTunnelFlagGateA",
    "C3:B9F2": "Event86_TwosonThreedTunnelFlagGateB",
    "C3:BA07": "Event88_TwosonThreedTunnelFlagGateC",
    "C3:BA1C": "Event87_TwosonThreedTunnelFlagGateD",
    "C3:BA31": "Event89_TwosonThreedTunnelFlagGateE",
    "C3:BA4F": "Event90_TwosonThreedTunnelFlagGateF",
    "C3:BA73": "Event94_95_98_TunnelGhostCommon",
    "C3:BA9C": "SetTunnelGhostDirectionRight",
    "C3:BA9F": "ApplyTunnelGhostDirectionAndHalt",
    "C3:BAA3": "RunTunnelGhostOneTextLoop",
    "C3:BAB5": "LoopTunnelGhostOneTextPartyTrack",
    "C3:BAC4": "RunTunnelGhostWarpTextHalt",
    "C3:BAD7": "RunTunnelGhostThreedWarpTextHalt",
    "C3:BB5C": "PrepareTunnelGhostActiveAreaWindow",
    "C3:BB73": "TrackPartyMemberForTunnelGhost",
    "C3:BB85": "LoopTrackPartyMemberForTunnelGhost",
    "C3:BB94": "Event93_TunnelGhostDirectionMoveAndYield",
    "C3:BBB7": "Event103_TunnelGhostFollowerLeftOffset",
    "C3:BBE0": "LoopEvent103_TunnelGhostFollowerLeftOffset",
    "C3:BC0A": "Event104_TunnelGhostFollowerRightOffset",
    "C3:BC33": "LoopEvent104_TunnelGhostFollowerRightOffset",
    "C3:BC5D": "Event105_TunnelGhostFollowerFarLeftOffset",
    "C3:BC86": "LoopEvent105_TunnelGhostFollowerFarLeftOffset",
    "C3:BCB0": "Event106_TunnelGhostFollowerFarRightOffset",
    "C3:BCD9": "LoopEvent106_TunnelGhostFollowerFarRightOffset",
    "C3:BD03": "PrepareTunnelGhostAreaWaitAndMovement",
    "C3:BD0E": "Event102_TunnelGhostRandomWanderPath",
    "C3:BD2E": "Event101_TunnelGhostMovementTextHalt",
    "C3:BD56": "Event107_TunnelGhostDiscoverFlagGate",
    "C3:BD80": "Event108_TunnelGhostSmallWanderPath",
    "C3:BDA0": "Event109_TunnelGhostPendingInteractionPath",
    "C3:BDC3": "Event110_TunnelGhostCoordinatePath",
    "C3:BE01": "Event111_VisualTypeTargetTracker",
    "C3:BE1C": "LoopEvent111_VisualTypeTargetTracker",
    "C3:BE2C": "Event112_PoseDescriptorTargetTracker",
    "C3:BE47": "LoopEvent112_PoseDescriptorTargetTracker",
    "C3:BE57": "Event113_TonyWakeupTextPath",
    "C3:BE80": "Event114_PartyPositionMovementTextHalt",
    "C0:A92D": "Script_SetTargetToVisualTypeSlotPosition_ReadWord",
    "C0:A938": "Script_SetTargetToPoseDescriptorSlotPosition_ReadWord",
    "C3:BEA4": "RunDoorCloseTempFlagTextHandoff",
    "C3:BED4": "RunDoorCloseTempFlagMovementReset",
    "C3:BEEE": "Event115_TempFlag1DoorCloseSequence",
    "C3:BF26": "LoopEvent115_WaitTempFlag1Clear",
    "C3:BF34": "LoopEvent115_WaitTempFlag1Set",
    "C3:BF4E": "Event116_TempFlag2DoorCloseSequence",
    "C3:BF87": "LoopEvent116_WaitTempFlag2Clear",
    "C3:BF98": "LoopEvent116_WaitTempFlag2Set",
    "C3:BFB2": "Event117_TempFlag3DoorCloseSequence",
    "C3:BFEB": "LoopEvent117_WaitTempFlag3Clear",
    "C3:BFFC": "LoopEvent117_WaitTempFlag3Set",
    "C3:C016": "Event118_TempFlag4DoorCloseSequence",
    "C3:C051": "LoopEvent118_WaitTempFlag4Clear",
    "C3:C062": "LoopEvent118_WaitTempFlag4Set",
    "C3:C07C": "Event119_TempFlag5DoorCloseSequence",
    "C3:C0BE": "LoopEvent119_WaitTempFlag5Clear",
    "C3:C0CF": "LoopEvent119_WaitTempFlag5Set",
    "C3:C0E4": "LoopEvent115_119PartyLookTask",
    "C3:C0F3": "Event468_StaggeredDoorCloseHalt",
    "C3:C101": "Event469_StaggeredDoorCloseHalt",
    "C3:C110": "Event470_StaggeredDoorCloseHalt",
    "C3:C11F": "Event471_StaggeredDoorCloseHalt",
    "C3:C12E": "Event472_StaggeredDoorCloseYieldHalt",
    "C3:C143": "RunStaggeredDoorCloseMovement",
    "C3:C1E0": "RunPositionDoorCloseOpeningPath",
    "C3:C20F": "RunPositionDoorCloseSoundPath",
    "C3:C227": "LoopMakePartyLookAtActiveEntity",
    "C3:C236": "Event120_RightStepTextYieldHandoff",
    "C3:C258": "Event121_DownLeftStepTextYieldHandoff",
    "C3:C282": "Event132_MoveTo1558_17B8ThenShakeLoop",
    "C3:C2AB": "LoopEvent132HorizontalShake",
    "C3:C2B8": "Event122_Set1728_1768TextYieldRelease",
    "C3:C2C8": "Event123_Set1748_1750Release",
    "C3:C2D1": "Event124_Set1758_1768Release",
    "C3:C2DA": "Event125_Set1770_1748Release",
    "C3:C2E3": "Event126_Set1788_1768Release",
    "C3:C2E9": "RunEvent122_126SharedPositionRelease",
    "C3:C2EF": "InitLeftFacingTempFlagMovementTo17C8_1768",
    "C3:C301": "LoopWaitForTempFlag1ClearToMove17C8_1768",
    "C3:C326": "Event127_Set1528_16E8TextYieldRelease",
    "C3:C336": "Event128_Set1540_16E0Release",
    "C3:C33F": "Event129_Set1558_16E8Release",
    "C3:C348": "Event130_Set1570_16D8Release",
    "C3:C351": "Event131_Set1588_16E8Release",
    "C3:C357": "RunEvent128_131SharedPositionRelease",
    "C3:C35D": "InitLeftFacingTempFlagMovementTo15F0_16E8",
    "C3:C36F": "LoopWaitForTempFlagMovementReadiness",
    "C3:C394": "Event133_PositionTextDoorMovementRelease",
    "C3:C3ED": "Event134_WaitAreaQueueKifuyaMovementHalt",
    "C3:C427": "Event135_RandomWalkTowardPartyLoop",
    "C3:C43C": "LoopEvent135_RandomWalkTowardParty",
    "C3:C46E": "Event136_PositionTextDoorSoundMovementHalt",
    "C3:C810": "LoopTeleportDestinationOffsetLeft",
    "C3:C81A": "LoopTeleportDestinationOffsetRight",
    "C3:C824": "LoopTeleportDestinationOffsetJitter",
    "C3:C832": "LoopTeleportDestinationLeftJitterA",
    "C3:C83A": "LoopTeleportDestinationLeftJitterB",
    "C3:C842": "LoopTeleportDestinationRightJitter",
    "C3:C84A": "LoopTeleportDestinationDownJitter",
    "C3:C852": "LoopTeleportDestinationUpJitterA",
    "C3:C85A": "LoopTeleportDestinationUpJitterB",
    "C3:C862": "LoopTeleportDestinationDownJitterReturn",
    "C3:C871": "LoopTeleportDestinationPausePulse",
    "C3:C879": "LoopTeleportDestinationPausePulseA",
    "C3:C87E": "LoopTeleportDestinationPausePulseB",
    "C3:C883": "LoopTeleportDestinationPausePulseC",
    "C3:C888": "LoopTeleportDestinationPausePulseD",
    "C3:C88D": "LoopTeleportDestinationPausePulseE",
    "C3:C892": "LoopTeleportDestinationPausePulseF",
    "C3:C897": "LoopTeleportDestinationPausePulseG",
    "C3:C8A3": "Event147_PrepareTeleportDestinationBD",
    "C3:C8B2": "Event148_PrepareTeleportDestinationBF",
    "C3:C8C1": "Event149_PrepareTeleportDestinationC1",
    "C3:C8D0": "Event150_PrepareTeleportDestinationC0",
    "C3:C8DF": "Event151_PrepareTeleportDestinationBE",
    "C3:C8EE": "Event152_PrepareTeleportDestinationBA",
    "C3:C8FD": "PrepareTeleportDestinationC3",
    "C3:C90C": "RunTeleportDestinationLeftRiseFadeHelper",
    "C3:C94E": "RunTeleportDestinationRiseFadeHelper",
    "C3:C990": "Event153_TeleportDestinationLeftArcRelease",
    "C3:C9E0": "Event155_TeleportDestinationLeftObscuredTextBC",
    "C3:CA3E": "Event154_TeleportDestinationRightArcRelease",
    "C3:CA8E": "Event156_TeleportDestinationRightObscuredTextBB",
    "C3:CAEA": "Event157_TeleportDestinationLeftLongArcRelease",
    "C3:CB38": "Event159_TeleportDestinationLeftTextBC",
    "C3:CB87": "Event158_TeleportDestinationRightLongArcRelease",
    "C3:CBD5": "Event160_TeleportDestinationRightTextBB",
    "C3:CC24": "RunTeleportFlyoverCoordinatePathA",
    "C3:CC5C": "RunTeleportFlyoverCoordinatePathB",
    "C3:CC94": "RunTeleportFlyoverOffsetPulseBursts",
    "C3:CCA8": "LoopTeleportFlyoverVerticalBob",
    "C3:CEA2": "LoopSpawnSkyRunnerElectricEffect",
    "C3:CEB9": "LoopSkyRunnerElectricEffectRise",
    "C3:DB7A": "RunBusTunnelBridgeRightTextHandoff",
    "C3:DBA0": "Event453_CopyPoseOffsetLeftUpPartyLookHalt",
    "C3:DBAC": "Event453_454_CommonPartyLookHalt",
    "C3:DBCC": "Event454_CopyPoseOffsetRightUpPartyLookHalt",
    "C3:DBDB": "CopyAnchorThenPrepareObscuredSimplePositionActor",
    "C3:DBE0": "PrepareObscuredSimplePositionActor",
    "C3:DF90": "RunRightwardLiveAreaTextYieldPath",
    "C3:DF9F": "LoopWaitUntilCurrentSlotInsideLiveArea",
    "C3:DFB5": "LoopRandomBounceOrDownwardWaitTask",
    "C3:DFD4": "ChooseDownwardVelocityAndWaitTimer",
    "C3:DFE4": "ApplyRandomBounceWaitTimer",
    "C0:A039": "PositionChangeCallback_C0A039",
    "C0:A06C": "ProjectWorldToScreen_DirectCamera39Event",
    "C0:5E76": "UpdateCurrentSlotCollisionCache",
    "C0:9451": "RestoreSavedCoordinateState",
    "C0:A82F": "DisableCurrentEntityCollision2",
    "C0:9FF0": "PhysicsCallback_C09FF0",
    "C0:A6DA": "ClearCurrentEntityCollision",
    "C0:A360": "UpdatePosition_WhenNoNeighbor_WithSpriteRefresh",
    "C0:AACD": "ReturnX0002",
    "C0:AA3F": "Script_SetVisualSetupBytesByMode",
    "C0:AAAC": "Script_RefreshCurrentSlotVisualProfile",
    "C0:C83B": "InstallScriptMovementVectorFromDirection",
    "C4:240A": "SetFullscreenColorWindowRangePreset",
    "C4:248A": "StopWh0HdmaChannel4AndClearWhsel",
    "C4:68B5": "TestValueLeftOfCurrentAnchorX",
    "C4:68DC": "TestValueAboveCurrentAnchorY",
    "C4:6C45": "SnapshotCurrentSlotAnchorToStagedPosition",
    "C4:7269": "ClassifyCurrentSlotAgainstAreaBounds",
    "C4:7499": "ApplyCurrentSlot0e5eBrightnessToPaletteRows",
    "C4:7A27": "StageBaseSlotRelativeWh0BoxMask",
    "C4:7A6B": "MirrorCurrentEntityYAroundTarget1002",
    "C4:7B77": "LoadIndexedWindowGfxAndReadVariantByte",
    "C4:800B": "UndrawFlyoverTextAndRestoreWorldDisplay",
    "C4:8B3B": "MakePartyLookAtActiveEntity",
    "C4:8BE1": "SimpleScreenPositionCallback",
    "C4:8C02": "SimpleScreenPositionCallbackOffset",
    "C4:8C3E": "CentreScreenOnEntityCallbackOffset",
    "C4:DD28": "DecompressItoiProductionIntroAssets",
    "C4:DDD0": "DecompressNintendoPresentationIntroAssets",
    "EF:0C87": "ReadActivePartySlotCacheWord",
    "EF:0C97": "ClearActivePartySlotCacheWord",
    "EF:0CA7": "CheckCurrentDeliveryRetryThreshold",
    "EF:0D23": "GetCurrentDeliveryRetryWait",
    "EF:0D46": "SeedCurrentDeliveryCountdown",
    "EF:0D73": "DecrementCurrentDeliveryCountdown",
    "EF:0D8D": "QueueCurrentDeliveryPointer1",
    "EF:0DFA": "QueueCurrentDeliveryPointer2",
    "EF:0E67": "GetCurrentDeliveryEnterSpeed",
    "EF:0E8A": "GetCurrentDeliveryExitSpeed",
    "EF:0F60": "CheckDeliveryServiceReadyForArrival",
    "EF:0FDB": "BeginDeliverySuccessArrivalState",
    "EF:0FF6": "ResetDeliveryArrivalState",
}

VAR_NAMES = {
    0x00: "!ACTIONSCRIPT_VARS_V0",
    0x01: "!ACTIONSCRIPT_VARS_V1",
    0x02: "!ACTIONSCRIPT_VARS_V2",
    0x03: "!ACTIONSCRIPT_VARS_V3",
    0x04: "!ACTIONSCRIPT_VARS_V4",
    0x05: "!ACTIONSCRIPT_VARS_V5",
    0x06: "!ACTIONSCRIPT_VARS_V6",
    0x07: "!ACTIONSCRIPT_VARS_V7",
}

FAMILY_DEFAULTS = {
    "movement-pulse-presets": {
        "output": DEFAULT_OUTPUT,
        "report": DEFAULT_REPORT,
        "manifest": DEFAULT_MANIFEST,
        "rows": SCRIPT_ROWS + PRESET_ROWS,
        "spans": [],
        "description": "Movement pulse preset family emitted as labeled event/actionscript macro assembly.",
        "next": "Promote another C3 family through this same generator pattern, then teach the bank scaffold to include source-form families in place of their opaque `script_event_payloads_0000_e450.asm` `db` corridors once enough families have stable labels and macro coverage.",
    },
    "timed-delivery-controller": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "timed_delivery_controller.asar.asm",
        "report": ROOT / "notes" / "c3-timed-delivery-source-pilot.md",
        "manifest": ROOT / "build" / "c3-timed-delivery-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:43DB", "C3:4508", "TimedDeliveryControllerAndPulseTask"),
        ],
        "description": "Timed-delivery controller proper emitted as labeled event/actionscript macro assembly. This covers the departure pulse task, event 499/500 setup, shared countdown/retry/readiness gates, success/failure branches, and arrival/departure movement loops.",
        "next": "The adjacent service-event movement scripts are now emitted by `--family service-event-movement`; inspect `C3:48C4..C3:4964` next and decide whether it belongs with that follow-up family or starts a neighboring service animation family.",
    },
    "service-event-movement": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "service_event_movement.asar.asm",
        "report": ROOT / "notes" / "c3-service-event-movement-source-pilot.md",
        "manifest": ROOT / "build" / "c3-service-event-movement-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4508", "C3:48C4", "ServiceEventMovementScripts"),
        ],
        "description": "Adjacent service-event movement scripts emitted as labeled event/actionscript macro assembly. This covers the event 547 camera-offset pulse, event 548/549 presentation paths, event 551-554 and 556-559 service movement paths, and event 555 brightness fade-out.",
        "next": "The neighboring service animation helpers and events are now emitted by `--family service-animation-helpers`; inspect `C3:4D39..C3:4E73` next.",
    },
    "service-animation-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "service_animation_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-service-animation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-service-animation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:48C4", "C3:4D39", "ServiceAnimationHelpersAndEvents"),
        ],
        "description": "Neighboring service animation helpers and events emitted as labeled event/actionscript macro assembly. This covers the reusable down/right/left facing gesture helper, event 560-563 presentation and read-task sequences, the compass direction countdown helper, and event 564-569 fixed-anchor/party-look-at movement presentations.",
        "next": "The neighboring presentation/effect corridor is now emitted by `--family service-presentation-effects`; inspect the larger `C3:4E73..C3:5F8B` payload cluster next.",
    },
    "service-presentation-effects": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "service_presentation_effects.asar.asm",
        "report": ROOT / "notes" / "c3-service-presentation-effects-source-pilot.md",
        "manifest": ROOT / "build" / "c3-service-presentation-effects-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4D39", "C3:4E73", "ServicePresentationEffects"),
        ],
        "description": "Service presentation/effect corridor emitted as labeled event/actionscript macro assembly. This covers the reusable falling/bounce helper, events 570-583 coordinate variants, traffic-light style offscreen waits, the Dosei-box event-flag gate, and the WH0 fullscreen color-window rise/fall effect sequence.",
        "next": "The first split from the larger `C3:4E73..C3:5F8B` payload cluster is now emitted by `--family itoi-production-intro`; continue at `C3:4FC7`.",
    },
    "itoi-production-intro": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "itoi_production_intro.asar.asm",
        "report": ROOT / "notes" / "c3-itoi-production-intro-source-pilot.md",
        "manifest": ROOT / "build" / "c3-itoi-production-intro-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4E73", "C3:4FC7", "ItoiProductionIntroScripts"),
        ],
        "description": "First split from the large `C3:4E73..C3:5F8B` payload cluster emitted as labeled event/actionscript macro assembly. This covers the common simple-screen-position actor initializer plus event 535-538 Itoi production intro movement/dialog paths and the temp-flag handoff loop.",
        "next": "The subsequent event 539-546 movement paths are now emitted by `--family intro-presentation-paths`; continue at `C3:51FD` with scripts 799-800 before deciding how to handle the large cast-scroll script 801.",
    },
    "intro-presentation-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "intro_presentation_paths.asar.asm",
        "report": ROOT / "notes" / "c3-intro-presentation-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-intro-presentation-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4FC7", "C3:51FD", "IntroPresentationPaths"),
        ],
        "description": "Second split from the large `C3:4E73..C3:5F8B` payload cluster emitted as labeled event/actionscript macro assembly. This covers event 539 plus event 540-546 intro/presentation movement paths, including the left-facing task loop and Nintendo presentation asset load path.",
        "next": "Scripts 799-800 are now emitted by `--family intro-cast-scroll-setup`; continue at `C3:5231` with script 801 as a separate cast-scroll/cast-spawn family.",
    },
    "intro-cast-scroll-setup": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "intro_cast_scroll_setup.asar.asm",
        "report": ROOT / "notes" / "c3-intro-cast-scroll-setup-source-pilot.md",
        "manifest": ROOT / "build" / "c3-intro-cast-scroll-setup-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:51FD", "C3:5231", "IntroCastScrollSetup"),
        ],
        "description": "Third split from the large `C3:4E73..C3:5F8B` payload cluster emitted as labeled event/actionscript macro assembly. This covers scripts 799-800: obscured, down-facing cast actor setup plus the WRAM `$0099` refresh gate.",
        "next": "Continue at `C3:5231` with script 801 as its own cast-scroll/cast-spawn source pilot; it needs additional native callback names and macro coverage before it should be promoted.",
    },
    "tunnel-ghost-zombie-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tunnel_ghost_zombie_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tunnel-ghost-zombie-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tunnel-ghost-zombie-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:B70C", "C3:BAA3", "TunnelGhostZombiePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the `C3:B70C` face-target/shake helper plus ebsrc scripts 73-90, including Threed/Twoson tunnel ghost gates, bikini-zombie movement/text paths, and the shared tunnel ghost text/direction setup.",
        "next": "Continue with the adjacent `C3:BAA3..C3:BD03` tunnel ghost common/warp helper corridor, or take the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "intro-cast-member-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "intro_cast_member_paths.asar.asm",
        "report": ROOT / "notes" / "c3-intro-cast-member-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-intro-cast-member-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:5F8B", "C3:62C0", "IntroCastMemberPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the cast-screen visibility/refresh task, the flat/depth actor initializers, and ebsrc scripts 802-803 and 809-825, including the short facing loops, priority variants, exit gestures, and broken phase distorter spawn handoff.",
        "next": "Continue at `C3:62C0..C3:6834` with scripts 826 and later cast-member movement paths, or take the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "teleport-destination-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "teleport_destination_paths.asar.asm",
        "report": ROOT / "notes" / "c3-teleport-destination-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-teleport-destination-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C94E", "C3:CC24", "TeleportDestinationPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the reusable teleport-destination rise/fade helper and ebsrc scripts 153-160, including left/right arc variants, obscured-body variants, destination entity preparation, and text-yield handoffs.",
        "next": "Continue with the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; nearby teleport-destination follow-ups include `C3:C824..C3:C8FD` and `C3:C90C..C94E`.",
    },
    "temp-flag-door-close-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "temp_flag_door_close_paths.asar.asm",
        "report": ROOT / "notes" / "c3-temp-flag-door-close-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-temp-flag-door-close-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:BEA4", "C3:C167", "TempFlagDoorClosePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the door-close/temp-flag handoff helpers, ebsrc scripts 115-119, the shared party-look task, scripts 468-472, and the movement helper at `C3:C143` used by the staggered variants.",
        "next": "Continue with `C3:C167..C1E0` only after the `C0:C682` callback contract is pinned, or take the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "party-look-window-gfx-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_look_window_gfx_paths.asar.asm",
        "report": ROOT / "notes" / "c3-party-look-window-gfx-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-look-window-gfx-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:3C1D", "C3:3DD4", "PartyLookWindowGfxPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the window-gfx variant loop, ebsrc script 467's random-facing idle loop, scripts 465-466 party-look movement paths, and the small field `$2B32` pulse task prefix at `C3:3DBE` used by those paths.",
        "next": "Continue with `C3:3DD4..C3:4392` only after the `C4:67E6` and later callback contracts are pinned, or take the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "tunnel-ghost-follower-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tunnel_ghost_follower_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tunnel-ghost-follower-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tunnel-ghost-follower-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:BB5C", "C3:BD03", "TunnelGhostFollowerPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the tunnel-ghost active-area setup helper, party-member tracking helper, event 93 movement/yield path, and ebsrc scripts 103-106 follower offset variants.",
        "next": "Continue with the adjacent `C3:BD03..C3:BEA4` corridor only after the `C0:A92D` callback contract is pinned, or take the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "tunnel-ghost-entity-setup-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tunnel_ghost_entity_setup_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tunnel-ghost-entity-setup-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tunnel-ghost-entity-setup-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:BD03", "C3:BEA4", "TunnelGhostEntitySetupPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the final tunnel-ghost setup corridor after the follower variants: a common active-area/movement initializer plus ebsrc scripts 101-102 and 107-114, including tunnel ghost entity placement, short movement/text handoffs, visual-type and pose-descriptor target tracking loops, and the Tony wake-up text path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:BEA4..C3:C167` temp-flag/door-close corridor is already promoted.",
    },
    "vehicle-coordinate-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "vehicle_coordinate_paths.asar.asm",
        "report": ROOT / "notes" / "c3-vehicle-coordinate-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-vehicle-coordinate-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6A41", "C3:6BB4", "VehicleCoordinatePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers a shared obscured vehicle actor initializer plus taxi/truck/red-car coordinate paths for ebsrc scripts 584-590, including the Onett door-close gate and Twoson bus-appearance gate.",
        "next": "Continue with the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent ready vehicle/movement follow-ups include `C3:6BB4..C3:6BEA` and `C3:6BEA..C3:6D18`.",
    },
    "boogy-tent-city-bus-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "boogy_tent_city_bus_paths.asar.asm",
        "report": ROOT / "notes" / "c3-boogy-tent-city-bus-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-boogy-tent-city-bus-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6BEA", "C3:6D18", "BoogyTentCityBusPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 592-596: the Boogy Tent Eye live-area wait/release path, two fixed coordinate movement releases, the city-bus coordinate path, and a z-bounce/text-yield visual release path.",
        "next": "Continue with the adjacent `C3:6D18..C3:6E41` region only after the `C0:CCCC` callback contract is pinned, or take the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "palette-fade-coordinate-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "palette_fade_coordinate_paths.asar.asm",
        "report": ROOT / "notes" / "c3-palette-fade-coordinate-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-palette-fade-coordinate-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7439", "C3:7545", "PaletteFadeCoordinatePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the reusable aligned-movement helper at `C3:7439` plus ebsrc scripts 633-637: two palette fade/yield loops, a blink-and-release path, a coordinate/sound/yield halt path, and a coordinate/text-yield release path.",
        "next": "Continue with the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; nearby ready follow-ups include the compact `C3:7545..C3:7559` and the larger `C3:7559..C3:7A7C` corridor after callback semantics are reviewed.",
    },
    "falling-bounce-yield-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "falling_bounce_yield_paths.asar.asm",
        "report": ROOT / "notes" / "c3-falling-bounce-yield-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-falling-bounce-yield-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:098B", "C3:0A1F", "FallingBounceYieldPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the shared wait/yield halt at `C3:098B`, ebsrc script 266's fixed coordinate move/yield halt, and ebsrc script 267's falling/bounce movement release sequence. The adjacent `C3:0A1F` Z-bounce task is labeled as an external target but left for a later split of the larger following row.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`, or split the adjacent `C3:0A1F..C3:0C55` row once the larger mixed sequence is reviewed.",
    },
    "pokey-bubble-monkey-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "pokey_bubble_monkey_paths.asar.asm",
        "report": ROOT / "notes" / "c3-pokey-bubble-monkey-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-pokey-bubble-monkey-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:0A1F", "C3:0C55", "PokeyBubbleMonkeyPaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam emitted as labeled event/actionscript macro assembly. This covers the short Z-bounce task and ebsrc scripts 268-283, including fixed-coordinate movement/yield paths, visual-type target tracking, Pokey battle staging, grouped party-member movement scripts, left/right movement releases, and the first Bubble Monkey route dispatchers that jump into the adjacent `C3:0C67` route family.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:0C55` helper and `C3:0C67..C3:0DCD` Bubble Monkey route family are already promoted.",
    },
    "teleport-destination-prelude-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "teleport_destination_prelude_paths.asar.asm",
        "report": ROOT / "notes" / "c3-teleport-destination-prelude-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-teleport-destination-prelude-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C824", "C3:C94E", "TeleportDestinationPreludePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the teleport-destination prelude helpers before the existing `C3:C94E..C3:CC24` pilot: a looping offset jitter task, a pause pulse task, ebsrc scripts 147-152, one additional destination-prepare variant, and the left-side rise/fade helper at `C3:C90C`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the main teleport-destination helper family is already emitted by `--family teleport-destination-paths`.",
    },
    "bus-tunnel-bridge-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bus_tunnel_bridge_paths.asar.asm",
        "report": ROOT / "notes" / "c3-bus-tunnel-bridge-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bus-tunnel-bridge-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:DB7A", "C3:DBF2", "BusTunnelBridgePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the bus-tunnel bridge right-side text handoff, ebsrc scripts 453-454's copied-pose offset party-look halt variants, their shared common tail, and the adjacent obscured simple-position actor helper at `C3:DBDB..C3:DBF2`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the larger adjacent `C3:DBF2..C3:DF90` corridor should be split only after its callback-heavy movement/text handoffs are reviewed.",
    },
    "anim-port-flag-switch": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "anim_port_flag_switch.asar.asm",
        "report": ROOT / "notes" / "c3-anim-port-flag-switch-source-pilot.md",
        "manifest": ROOT / "build" / "c3-anim-port-flag-switch-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:835D", "C3:83BC", "AnimPortFlagSwitch"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the tempvar-indexed helper used by ebsrc scripts 688-691 to write the two animation-port event flags in all four binary combinations.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; scripts 688-691 in the adjacent `C3:83BC..C3:8978` region are the natural semantic consumer of this helper.",
    },
    "var0-animation-collision-probe": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "var0_animation_collision_probe.asar.asm",
        "report": ROOT / "notes" / "c3-var0-animation-collision-probe-source-pilot.md",
        "manifest": ROOT / "build" / "c3-var0-animation-collision-probe-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A20E", "C3:A271", "Var0AnimationCollisionProbe"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the var0-selected animation loop that runs until the active entity leaves the live-area window plus the adjacent collision-probe refresh task commonly started by movement scripts.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; this helper cluster is a semantic neighbor of the existing movement pulse preset family.",
    },
    "area-wait-random-wander-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "area_wait_random_wander_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-area-wait-random-wander-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-area-wait-random-wander-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:AB67", "C3:ABE0", "AreaWaitRandomWanderHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers common area-aware movement helpers: moving away from a target vector, waiting for the player to leave or enter the active area, and the random wander loop that chooses direction, movement duration, and wait timer.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:ABE0` wait helper is still part of the larger fade/teleport handoff row and should be split with that context.",
    },
    "teleport-flyover-coordinate-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "teleport_flyover_coordinate_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-teleport-flyover-coordinate-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-teleport-flyover-coordinate-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:CC24", "C3:CC94", "TeleportFlyoverCoordinateHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers two paired coordinate path helpers used by nearby teleport/flyover scripts 161 and 164, each walking a five-point path through V6/V7 coordinates before returning.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; these helpers are semantic neighbors of the teleport-destination path pilots.",
    },
    "threed-fight-matent-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "threed_fight_matent_paths.asar.asm",
        "report": ROOT / "notes" / "c3-threed-fight-matent-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-threed-fight-matent-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6BB4", "C3:6BEA", "ThreedFightMatentPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the small V3-gated vertical bounce loop at `C3:6BB4` and ebsrc script 591, which snapshots the current anchor, waits for the player to leave the active area, waits for battle/enemy-touch state to clear, queues `MSG_EVT_THRK_FIGHT_MATENT`, and halts.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; this closes the compact gap between the vehicle coordinate paths and Boogy Tent/city bus pilots.",
    },
    "position-door-close-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "position_door_close_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-position-door-close-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-position-door-close-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C1E0", "C3:C227", "PositionDoorCloseHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the paired helper paths used by ebsrc scripts 473-475: an opening positioning path that starts the party-look task at `C3:C227`, and a follow-up coordinate move that plays the door-close sound.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; this closes the compact gap immediately before the existing position/text-yield path pilot.",
    },
    "position-text-door-sound-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "position_text_door_sound_paths.asar.asm",
        "report": ROOT / "notes" / "c3-position-text-door-sound-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-position-text-door-sound-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C35D", "C3:C4CF", "PositionTextDoorSoundPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 133-136: the left-facing temp-flag movement helper, a position/text/door movement release, the Kifuya active-area text handoff, a random party-following movement loop, and a door-sound movement/text-yield path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the immediate `C3:C4CF` continuation reaches script 137 and is blocked until the `C0:A8B3` callroutine contract is pinned.",
    },
    "bubble-monkey-route-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bubble_monkey_route_paths.asar.asm",
        "report": ROOT / "notes" / "c3-bubble-monkey-route-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bubble-monkey-route-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:0C67", "C3:0DCD", "BubbleMonkeyRoutePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 284-286 and nearby route helpers: a looping long coordinate patrol route, Bubble Monkey goodbye movement/text handoffs, the shared multi-point coordinate route at `C3:0D3C`, and the Giygas-win-flag wait/release path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the immediate `C3:0DCD` continuation reaches a `C0:A8B3` callroutine contract that should be pinned before promotion.",
    },
    "tstage-performance-movement-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_performance_movement_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-performance-movement-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-performance-movement-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:2CD2", "C3:2DFE", "TStagePerformanceMovementPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the looping stage-actor vertical bounce helper plus ebsrc script 399's long theater-stage performance movement path, with velocity pulses, facing changes, timed pauses, and release.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; nearby stage text/path continuations are blocked by `C4:74A8` until that callroutine contract is pinned.",
    },
    "stage-visual-pulse-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "stage_visual_pulse_paths.asar.asm",
        "report": ROOT / "notes" / "c3-stage-visual-pulse-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-stage-visual-pulse-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:33DD", "C3:34FF", "StageVisualPulsePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the stage-facing visual pulse helper at `C3:33DD`, ebsrc script 435's long pulse-and-velocity release sequence, and ebsrc script 436's obscured stage slide release path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent script 438 continuation is blocked by `C4:74A8` until that callroutine contract is pinned.",
    },
    "leftward-bounds-release-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "leftward_bounds_release_paths.asar.asm",
        "report": ROOT / "notes" / "c3-leftward-bounds-release-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-leftward-bounds-release-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4392", "C3:43DB", "LeftwardBoundsReleasePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the shared leftward movement path used by ebsrc scripts 532-533 plus its concurrent bounds-watch task, which releases the visual entity once X/Y threshold checks are satisfied.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the preceding `C3:3DD4..C3:4392` corridor is still blocked on callback contracts.",
    },
    "anim-port-direction-tasks": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "anim_port_direction_tasks.asar.asm",
        "report": ROOT / "notes" / "c3-anim-port-direction-tasks-source-pilot.md",
        "manifest": ROOT / "build" / "c3-anim-port-direction-tasks-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:8978", "C3:89BD", "AnimPortDirectionTasks"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the paired tasks used by ebsrc scripts 713-714: a V4/animation-port driven direction loop and the adjacent blink animation loop at the start of the larger `C3:899E` row.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the rest of the larger `C3:89BD..C3:9AC7` corridor should be split by local script/task boundaries before promotion.",
    },
    "rightward-live-area-bounce-yield": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "rightward_live_area_bounce_yield.asar.asm",
        "report": ROOT / "notes" / "c3-rightward-live-area-bounce-yield-source-pilot.md",
        "manifest": ROOT / "build" / "c3-rightward-live-area-bounce-yield-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:DF90", "C3:DFE8", "RightwardLiveAreaBounceYield"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the compact right-facing movement/yield path at `C3:DF90` plus its concurrent randomized bounce/downward wait task split across `C3:DFB5` and `C3:DFD4` in ebsrc.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:DBF2..C3:DF90` remains larger and should be split only after its local movement/text handoffs are reviewed.",
    },
    "var4-animation-side-step-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "var4_animation_side_step_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-var4-animation-side-step-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-var4-animation-side-step-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1D2D", "C3:1D4F", "Var4TimedAnimationPulse"),
            ("C3:1EC1", "C3:1EEF", "SideStepPulseHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the V4-controlled animation pulse task used by the common `C3:1D4F` setup helper plus the paired right/left side-step pulse helpers used by nearby Twoson/traffic-style movement scripts.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:1D4F..C3:1EC1` remains blocked on C4 callback contracts before the larger script setup corridor can be promoted.",
    },
    "window-gfx-loader-prologue": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "window_gfx_loader_prologue.asar.asm",
        "report": ROOT / "notes" / "c3-window-gfx-loader-prologue-source-pilot.md",
        "manifest": ROOT / "build" / "c3-window-gfx-loader-prologue-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:3BFB", "C3:3C1D", "WindowGfxLoaderPrologue"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This closes the compact window-gfx loader prologue immediately before the existing `C3:3C1D..C3:3DD4` party-look/window-gfx source pilot, including the indexed gfx-load loop and flyover-text undraw return.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the following `C3:3C1D..C3:3DD4` family is already promoted, while `C3:3DD4..C3:4392` remains blocked on C4 callback contracts.",
    },
    "tunnel-ghost-warp-text-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tunnel_ghost_warp_text_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-tunnel-ghost-warp-text-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tunnel-ghost-warp-text-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:BAA3", "C3:BAD7", "TunnelGhostWarpTextHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the compact tunnel-ghost text helpers used by ebsrc scripts 87, 88, and 96: a looping `MSG_EVT_GHOST_1` follower/position update path and a `MSG_EVT_GHOST_WARP` halt path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the preceding tunnel ghost/zombie family and following tunnel ghost follower family are already promoted.",
    },
    "movement-vector-core-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "movement_vector_core_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-movement-vector-core-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-movement-vector-core-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:AA1E", "C3:AA38", "MovementVectorInitHelpers"),
            ("C3:AB37", "C3:AB67", "MovementVectorWaitHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers common C3 movement-vector helpers: applying temp direction to the current movement vector, initializing default movement physics/pulse/collision tasks, setting simple-screen callbacks, refreshing direction/visual profile from the active target vector, and waiting for movement completion.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:AB67..C3:ABE0` is already promoted, while larger callers should now be easier to read through these common helper names.",
    },
    "facing-pulse-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "facing_pulse_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-facing-pulse-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-facing-pulse-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7545", "C3:756D", "FacingPulseHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the paired two-cycle facing pulse helpers used by nearby ebsrc scripts 717, 724, 729, 741, 742, 744, and 755, alternating right/left or left/right visual countdown states before returning.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:756D..C3:7A7C` still contains larger movement/text scripts that should be split by local script boundaries.",
    },
    "teleport-flyover-pulse-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "teleport_flyover_pulse_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-teleport-flyover-pulse-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-teleport-flyover-pulse-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C810", "C3:C824", "TeleportDestinationOffsetPulseHelpers"),
            ("C3:CC94", "C3:CCB5", "TeleportFlyoverPulseHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers compact teleport/flyover pulse helpers around already-promoted teleport families: V1 offset drift loops before `C3:C824`, repeated offset-jitter task bursts used by ebsrc script 170, and the vertical bob loop at `C3:CCA8`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent teleport destination/flyover coordinate families are already promoted.",
    },
    "sky-runner-electric-effect-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "sky_runner_electric_effect_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-sky-runner-electric-effect-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-sky-runner-electric-effect-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:CEA2", "C3:CEC7", "SkyRunnerElectricEffectHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the Sky Runner electric-effect helper pair near the teleport/flyover scripts: a periodic effect-spawn loop and a companion loop that copies pose descriptor `$00D1`, offsets it upward, and repeats every frame.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:CCB5..C3:CEA2` and following script payloads should be split only after their local script/task boundaries are reviewed.",
    },
    "small-terminal-helper-cleanup": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "small_terminal_helper_cleanup.asar.asm",
        "report": ROOT / "notes" / "c3-small-terminal-helper-cleanup-source-pilot.md",
        "manifest": ROOT / "build" / "c3-small-terminal-helper-cleanup-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:0C55", "C3:0C67", "SmallMovementPresetField2B32RefreshHelper"),
            ("C3:3399", "C3:33DD", "FacingVisualCountdownPulseHelpers"),
            ("C3:6A3E", "C3:6A41", "CastPathReleaseTail"),
            ("C3:A209", "C3:A20E", "DelayThenReleaseHelper"),
            ("C3:A271", "C3:A272", "EndTaskHelper"),
        ],
        "description": "High-ranked source-pilot frontier cleanup emitted as labeled event/actionscript macro assembly. This covers compact terminal helpers from the ready frontier: a movement preset/field refresh helper, four one-shot facing visual countdown pulses, a cast-path release tail, the four-frame delay release helper, and a single-byte end-task helper.",
        "next": "Continue with larger ready terminal batches from `notes/c3-source-pilot-frontier.md`; this removes the small top-ranked crumbs so the frontier is easier to scan.",
    },
    "cast-screen-tenda-king-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "cast_screen_tenda_king_paths.asar.asm",
        "report": ROOT / "notes" / "c3-cast-screen-tenda-king-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-cast-screen-tenda-king-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6834", "C3:6A41", "CastScreenTendaKingPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the cast-screen Tenda/King/Ness-posing path cluster around ebsrc scripts 845-858: wait-and-spawn release helpers, left/right step-and-halt variants, a cast-screen facing cycle until invisible, and projected pose setup for the final Ness-posing actor.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the preceding `C3:62C0..C3:6834` corridor is still larger and should be split by script boundaries.",
    },
    "live-area-facing-movement-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "live_area_facing_movement_paths.asar.asm",
        "report": ROOT / "notes" / "c3-live-area-facing-movement-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-live-area-facing-movement-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:83BC", "C3:8515", "LiveAreaFacingMovementPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the random facing-cycle helper and ebsrc scripts 693-695: live-area facing loops with fast/slow timing plus a longer movement path that yields to text after walking through fixed coordinates.",
        "next": "Continue at the adjacent `C3:8515..C3:8978` portion only after the `C0:A92D` callroutine contract is pinned, or take another ready terminal batch from `notes/c3-source-pilot-frontier.md`.",
    },
    "onett-townhall-movement-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "onett_townhall_movement_paths.asar.asm",
        "report": ROOT / "notes" / "c3-onett-townhall-movement-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-onett-townhall-movement-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:89BD", "C3:8B7F", "OnettTownHallMovementPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the ebsrc script 715-721 corridor: blink/release and offset-pose helpers, the long Onett town hall movement/dialog path, the paired door-sound task, and short coordinate movement variants that end by release or task halt.",
        "next": "Continue with the remaining `C3:8B7F..C3:9AC7` terminal corridor after reviewing its local script boundaries, or take another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "onett-townhall-door-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "onett_townhall_door_paths.asar.asm",
        "report": ROOT / "notes" / "c3-onett-townhall-door-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-onett-townhall-door-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:8B7F", "C3:8DB3", "OnettTownHallDoorPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the ebsrc script 722-729 continuation: doorway movement paths, door open/close sound timing, facing-pulse waits, text-yield handoffs, and the longer town hall door-sound movement path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:8DB3` continuation reaches script 730's perpetual direction task and should be split separately.",
    },
    "direction-tracker-townhall-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "direction_tracker_townhall_paths.asar.asm",
        "report": ROOT / "notes" / "c3-direction-tracker-townhall-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-direction-tracker-townhall-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:8DB3", "C3:8EF1", "DirectionTrackerTownHallPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the ebsrc script 730-737 prefix: a perpetual direction-tracker task, movement paths that return into that tracker, a sound/text movement halt, a random-facing text halt, and the first direction setter that jumps to the shared `C3:8F06` common tail.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:8F06` continuation should be promoted with scripts 737-744 after its shared local labels are reviewed.",
    },
    "position-text-yield-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "position_text_yield_paths.asar.asm",
        "report": ROOT / "notes" / "c3-position-text-yield-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-position-text-yield-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C227", "C3:C35D", "PositionTextYieldPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the party-look-at-active-entity loop plus ebsrc scripts 120-132, including text-yield handoffs, fixed coordinate placement helpers, temporary-flag wait loops, and short movement releases into adjacent helper `C3:C35D`.",
        "next": "Continue with the adjacent `C3:C35D..C3:C810` region only after splitting its larger mixed payload, or take the next high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
}


@dataclass(frozen=True)
class Operand:
    kind: str
    value: int | Address


@dataclass(frozen=True)
class Instruction:
    address: Address
    opcode_byte: int
    opcode: Opcode
    raw: bytes
    operands: tuple[Operand, ...]
    call_arg_count: int | None = None


@dataclass(frozen=True)
class RowSource:
    address: Address
    key: str
    name: str
    size: int
    raw: bytes
    instructions: tuple[Instruction, ...]
    source: str = "source-data-map"


def parse_address_key(text: str) -> Address:
    bank_text, offset_text = text.split(":", 1)
    return Address(int(bank_text, 16), int(offset_text, 16))


def fmt_byte(value: int) -> str:
    return f"${value & 0xFF:02X}"


def fmt_word(value: int) -> str:
    return f"${value & 0xFFFF:04X}"


def fmt_long(value: int) -> str:
    return f"${value & 0xFFFFFF:06X}"


def sanitize_symbol(text: str) -> str:
    text = text.replace("::", "_")
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "Target"
    if text[0].isdigit():
        text = f"Addr_{text}"
    return text


def preferred_label(address: Address, names: dict[str, list[str]]) -> str:
    if address.key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[address.key]
    if names.get(address.key):
        return names[address.key][0]
    return f"Local_{address.bank:02X}{address.offset:04X}"


def row_name(row: dict[str, Any], names: dict[str, list[str]]) -> str:
    address = parse_address_key(row["address"])
    if address.key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[address.key]
    if row.get("name"):
        return str(row["name"])
    if names.get(address.key):
        return names[address.key][0]
    return f"Script_{address.bank:02X}{address.offset:04X}"


def load_row_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, Any]] = {}
    for row in payload["include_rows"]:
        address = row.get("address")
        if address:
            rows[address] = row
    return rows


def decode_exact_row(raw: bytes, start: Address) -> tuple[Instruction, ...]:
    instructions: list[Instruction] = []
    pos = 0
    while pos < len(raw):
        address = Address(start.bank, start.offset + pos)
        raw_start = pos
        opcode_byte = raw[pos]
        pos += 1
        opcode = OPCODES.get(opcode_byte)
        if opcode is None:
            raise ValueError(f"unknown opcode ${opcode_byte:02X} at {address.key}")

        operands: list[Operand] = []
        call_arg_count: int | None = None
        for spec in opcode.args:
            if spec == "byte":
                operands.append(Operand(spec, raw[pos]))
                pos += 1
            elif spec == "word":
                operands.append(Operand(spec, read_u16(raw, pos)))
                pos += 2
            elif spec == "shortptr":
                operands.append(Operand(spec, Address(start.bank, read_u16(raw, pos))))
                pos += 2
            elif spec == "callbackptr":
                operands.append(Operand(spec, Address(0xC0, read_u16(raw, pos))))
                pos += 2
            elif spec == "ptr3":
                operands.append(Operand(spec, Address(raw[pos + 2], read_u16(raw, pos))))
                pos += 3
            elif spec == "callroutine":
                target = Address(raw[pos + 2], read_u16(raw, pos))
                pos += 3
                operands.append(Operand(spec, target))
                if target.key == "C0:9F82":
                    count = raw[pos]
                    pos += 1
                    operands.append(Operand("call_wordlist_count", count))
                    for _ in range(count):
                        operands.append(Operand("call_wordlist_word", read_u16(raw, pos)))
                        pos += 2
                    continue
                count = CALL_ARG_COUNTS.get(target.key)
                if count is None:
                    raise ValueError(f"unknown callroutine arg count for {target.key} at {address.key}")
                call_arg_count = count
                for _ in range(count):
                    operands.append(Operand("call_arg_byte", raw[pos]))
                    pos += 1
            elif spec == "wordlist":
                count = raw[pos]
                pos += 1
                operands.append(Operand("wordlist_count", count))
                for _ in range(count):
                    operands.append(Operand("wordlist_shortptr", Address(start.bank, read_u16(raw, pos))))
                    pos += 2
            else:
                raise ValueError(f"unhandled operand spec {spec!r}")

        if pos > len(raw):
            raise ValueError(f"instruction at {address.key} runs past row end")
        instructions.append(
            Instruction(
                address=address,
                opcode_byte=opcode_byte,
                opcode=opcode,
                raw=raw[raw_start:pos],
                operands=tuple(operands),
                call_arg_count=call_arg_count,
            )
        )
    return tuple(instructions)


def load_rows(
    rom: bytes,
    rows_by_address: dict[str, dict[str, Any]],
    row_keys: list[str],
    names: dict[str, list[str]],
) -> list[RowSource]:
    rows: list[RowSource] = []
    for key in row_keys:
        row = rows_by_address.get(key)
        if not row:
            raise KeyError(f"{key} is not an addressed include row in the source/data map")
        address = parse_address_key(key)
        size = int(row["size"])
        file_offset = hirom_to_file_offset(address.bank, address.offset, len(rom))
        if file_offset is None:
            raise ValueError(f"{key} is not a mapped HiROM address")
        raw = rom[file_offset : file_offset + size]
        rows.append(
            RowSource(
                address=address,
                key=key,
                name=sanitize_symbol(row_name(row, names)),
                size=size,
                raw=raw,
                instructions=decode_exact_row(raw, address),
                source=row.get("path") or "source-data-map",
            )
        )
    return rows


def load_spans(
    rom: bytes,
    spans: list[tuple[str, str, str]],
    names: dict[str, list[str]],
) -> list[RowSource]:
    rows: list[RowSource] = []
    for start_key, end_key, name in spans:
        start = parse_address_key(start_key)
        end = parse_address_key(end_key)
        if start.bank != end.bank:
            raise ValueError(f"span cannot cross banks: {start_key}..{end_key}")
        size = end.offset - start.offset
        if size <= 0:
            raise ValueError(f"span must have positive size: {start_key}..{end_key}")
        file_offset = hirom_to_file_offset(start.bank, start.offset, len(rom))
        if file_offset is None:
            raise ValueError(f"{start_key} is not a mapped HiROM address")
        raw = rom[file_offset : file_offset + size]
        display_name = LABEL_OVERRIDES.get(start.key) or names.get(start.key, [name])[0]
        rows.append(
            RowSource(
                address=start,
                key=f"{start.key}..{end.key}",
                name=sanitize_symbol(display_name),
                size=size,
                raw=raw,
                instructions=decode_exact_row(raw, start),
                source="explicit-span",
            )
        )
    return rows


def collect_selected_ranges(rows: list[RowSource]) -> list[tuple[int, int]]:
    return [(row.address.long, row.address.long + row.size) for row in rows]


def in_selected_ranges(address: Address, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= address.long < end for start, end in ranges)


def collect_c3_targets(rows: list[RowSource]) -> set[str]:
    targets: set[str] = set()
    for row in rows:
        for instruction in row.instructions:
            for operand in instruction.operands:
                if isinstance(operand.value, Address) and operand.value.bank == 0xC3:
                    targets.add(operand.value.key)
    return targets


def collect_label_map(rows: list[RowSource], names: dict[str, list[str]]) -> dict[str, str]:
    ranges = collect_selected_ranges(rows)
    labels: dict[str, str] = {row.key: row.name for row in rows}
    instruction_addresses = {
        instruction.address.key
        for row in rows
        for instruction in row.instructions
    }
    for key, label in LABEL_OVERRIDES.items():
        address = parse_address_key(key)
        if key in labels:
            continue
        if in_selected_ranges(address, ranges) and key in instruction_addresses:
            labels[key] = sanitize_symbol(label)
    for key in collect_c3_targets(rows):
        address = parse_address_key(key)
        if key in labels:
            continue
        if in_selected_ranges(address, ranges) and key in instruction_addresses:
            labels[key] = sanitize_symbol(preferred_label(address, names))
    return labels


def constant_name(address: Address, names: dict[str, list[str]]) -> str:
    if address.key in LABEL_OVERRIDES:
        return sanitize_symbol(LABEL_OVERRIDES[address.key])
    if names.get(address.key):
        return sanitize_symbol(names[address.key][0])
    return f"Target_{address.bank:02X}{address.offset:04X}"


def operand_expr(
    operand: Operand,
    *,
    instruction: Instruction,
    index: int,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
) -> str:
    if operand.kind == "byte":
        value = int(operand.value)
        var_slot_operands = {
            "EVENT_SET_VAR": {0},
            "EVENT_WRITE_VAR_TO_TEMPVAR": {0},
            "EVENT_WRITE_TEMPVAR_TO_VAR": {0},
            "EVENT_WRITE_VAR_TO_WAIT_TIMER": {0},
            "EVENT_SET_ANIMATION_FRAME_VAR": {0},
            "EVENT_BINOP": {0},
        }
        if index in var_slot_operands.get(instruction.opcode.name, set()):
            return VAR_NAMES.get(value, fmt_byte(value))
        return fmt_byte(value)
    if operand.kind in {"word", "call_arg_byte"}:
        value = int(operand.value)
        return fmt_byte(value) if operand.kind == "call_arg_byte" else fmt_word(value)
    if operand.kind in {"wordlist_count", "call_wordlist_count"}:
        return str(int(operand.value))
    if operand.kind == "call_wordlist_word":
        return fmt_word(int(operand.value))

    if not isinstance(operand.value, Address):
        raise TypeError(f"expected address operand, got {operand.value!r}")

    target = operand.value
    if operand.kind in {"shortptr", "wordlist_shortptr"} and target.key in labels:
        return labels[target.key]

    name = constant_name(target, names)
    symbol = f"!{name}"
    if operand.kind in {"shortptr", "callbackptr", "wordlist_shortptr"}:
        constants.setdefault(symbol, fmt_word(target.offset))
    else:
        constants.setdefault(symbol, fmt_long(target.long))
    return symbol


def macro_name(instruction: Instruction) -> str:
    if instruction.opcode.name == "EVENT_CALLROUTINE":
        if (
            instruction.operands
            and isinstance(instruction.operands[0].value, Address)
            and instruction.operands[0].value.key == "C0:9F82"
        ):
            count = next(
                int(operand.value)
                for operand in instruction.operands
                if operand.kind == "call_wordlist_count"
            )
            return f"EVENT_CHOOSE_RANDOM_SCRIPT_WORD_{count}"
        return f"EVENT_CALLROUTINE_{instruction.call_arg_count or 0}"
    if instruction.opcode.name in {"EVENT_SWITCH_JUMP_TEMPVAR", "EVENT_SWITCH_CALL_TEMPVAR"}:
        return f"{instruction.opcode.name}_{instruction.operands[0].value}"
    return instruction.opcode.name


def render_instruction(
    instruction: Instruction,
    *,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
) -> str:
    rendered_operands = [
        operand_expr(
            operand,
            instruction=instruction,
            index=index,
            labels=labels,
            names=names,
            constants=constants,
        )
        for index, operand in enumerate(instruction.operands)
    ]
    args = ", ".join(rendered_operands)
    raw = " ".join(f"{byte:02X}" for byte in instruction.raw)
    if args:
        return f"    %{macro_name(instruction)}({args}) ; {instruction.address.key}  {raw}"
    return f"    %{macro_name(instruction)}() ; {instruction.address.key}  {raw}"


def macro_definitions(used_macros: set[str]) -> list[str]:
    bodies = {
        "EVENT_BREAK_IF_FALSE": ["    db $16", "    dw <target>"],
        "EVENT_BINOP": ["    db $14, <var>, <op>", "    dw <value>"],
        "EVENT_BINOP_TEMPVAR": ["    db $27, <op>", "    dw <value>"],
        "EVENT_CALLROUTINE_0": ["    db $42", "    dl <target>"],
        "EVENT_CALLROUTINE_1": ["    db $42", "    dl <target>", "    db <arg0>"],
        "EVENT_CALLROUTINE_2": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>"],
        "EVENT_CALLROUTINE_3": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>, <arg2>"],
        "EVENT_CALLROUTINE_4": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>, <arg2>, <arg3>"],
        "EVENT_CLEAR_TICK_CALLBACK": ["    db $0F"],
        "EVENT_END": ["    db $00"],
        "EVENT_END_LAST_TASK": ["    db $13"],
        "EVENT_END_TASK": ["    db $0C"],
        "EVENT_HALT": ["    db $09"],
        "EVENT_LOOP": ["    db $01, <count>"],
        "EVENT_LOOP_END": ["    db $02"],
        "EVENT_LOOP_TEMPVAR": ["    db $24"],
        "EVENT_PAUSE": ["    db $06, <frames>"],
        "EVENT_SET_ANIMATION": ["    db $3B, <animation>"],
        "EVENT_SET_PHYSICS_CALLBACK": ["    db $25", "    dw <target>"],
        "EVENT_SET_POSITION_CHANGE_CALLBACK": ["    db $23", "    dw <target>"],
        "EVENT_SET_PRIORITY": ["    db $43, <priority>"],
        "EVENT_SET_TICK_CALLBACK": ["    db $08", "    dl <target>"],
        "EVENT_SET_VAR": ["    db $0E, <var>", "    dw <value>"],
        "EVENT_SET_VELOCITIES_ZERO": ["    db $39"],
        "EVENT_SET_X_VELOCITY": ["    db $3F", "    dw <value>"],
        "EVENT_SET_X_VELOCITY_RELATIVE": ["    db $2E", "    dw <value>"],
        "EVENT_SET_X": ["    db $28", "    dw <value>"],
        "EVENT_SET_X_RELATIVE": ["    db $2B", "    dw <value>"],
        "EVENT_SET_Y": ["    db $29", "    dw <value>"],
        "EVENT_SET_Y_RELATIVE": ["    db $2C", "    dw <value>"],
        "EVENT_SET_Y_VELOCITY": ["    db $40", "    dw <value>"],
        "EVENT_SET_Y_VELOCITY_RELATIVE": ["    db $2F", "    dw <value>"],
        "EVENT_SET_Z": ["    db $2A", "    dw <value>"],
        "EVENT_SET_Z_RELATIVE": ["    db $2D", "    dw <value>"],
        "EVENT_SET_Z_VELOCITY": ["    db $41", "    dw <value>"],
        "EVENT_SET_Z_VELOCITY_RELATIVE": ["    db $30", "    dw <value>"],
        "EVENT_SHORTCALL": ["    db $1A", "    dw <target>"],
        "EVENT_SHORTCALL_CONDITIONAL": ["    db $0A", "    dw <target>"],
        "EVENT_SHORTCALL_CONDITIONAL_NOT": ["    db $0B", "    dw <target>"],
        "EVENT_SHORTJUMP": ["    db $19", "    dw <target>"],
        "EVENT_SHORT_RETURN": ["    db $1B"],
        "EVENT_START_TASK": ["    db $07", "    dw <target>"],
        "EVENT_WRITE_VAR_TO_TEMPVAR": ["    db $20, <var>"],
        "EVENT_WRITE_BYTE_WRAM": ["    db $12", "    dw <addr>", "    db <value>"],
        "EVENT_WRITE_WORD_WRAM": ["    db $15", "    dw <addr>", "    dw <value>"],
        "EVENT_WRITE_TEMPVAR_TO_VAR": ["    db $1F, <var>"],
        "EVENT_WRITE_VAR_TO_WAIT_TIMER": ["    db $21, <var>"],
        "EVENT_WRITE_WORD_TEMPVAR": ["    db $1D", "    dw <value>"],
        "EVENT_WRITE_WRAM_TEMPVAR": ["    db $1E", "    dw <addr>"],
        "EVENT_WRITE_TEMPVAR_WAITTIMER": ["    db $44"],
    }
    args = {
        "EVENT_BREAK_IF_FALSE": "target",
        "EVENT_BINOP": "var, op, value",
        "EVENT_BINOP_TEMPVAR": "op, value",
        "EVENT_CALLROUTINE_0": "target",
        "EVENT_CALLROUTINE_1": "target, arg0",
        "EVENT_CALLROUTINE_2": "target, arg0, arg1",
        "EVENT_CALLROUTINE_3": "target, arg0, arg1, arg2",
        "EVENT_CALLROUTINE_4": "target, arg0, arg1, arg2, arg3",
        "EVENT_LOOP": "count",
        "EVENT_PAUSE": "frames",
        "EVENT_SET_ANIMATION": "animation",
        "EVENT_SET_PHYSICS_CALLBACK": "target",
        "EVENT_SET_POSITION_CHANGE_CALLBACK": "target",
        "EVENT_SET_PRIORITY": "priority",
        "EVENT_SET_TICK_CALLBACK": "target",
        "EVENT_SET_VAR": "var, value",
        "EVENT_SET_X_VELOCITY": "value",
        "EVENT_SET_X_VELOCITY_RELATIVE": "value",
        "EVENT_SET_X": "value",
        "EVENT_SET_X_RELATIVE": "value",
        "EVENT_SET_Y": "value",
        "EVENT_SET_Y_RELATIVE": "value",
        "EVENT_SET_Y_VELOCITY": "value",
        "EVENT_SET_Y_VELOCITY_RELATIVE": "value",
        "EVENT_SET_Z": "value",
        "EVENT_SET_Z_RELATIVE": "value",
        "EVENT_SET_Z_VELOCITY": "value",
        "EVENT_SET_Z_VELOCITY_RELATIVE": "value",
        "EVENT_SHORTCALL": "target",
        "EVENT_SHORTCALL_CONDITIONAL": "target",
        "EVENT_SHORTCALL_CONDITIONAL_NOT": "target",
        "EVENT_SHORTJUMP": "target",
        "EVENT_START_TASK": "target",
        "EVENT_WRITE_VAR_TO_TEMPVAR": "var",
        "EVENT_WRITE_BYTE_WRAM": "addr, value",
        "EVENT_WRITE_WORD_WRAM": "addr, value",
        "EVENT_WRITE_TEMPVAR_TO_VAR": "var",
        "EVENT_WRITE_VAR_TO_WAIT_TIMER": "var",
        "EVENT_WRITE_WORD_TEMPVAR": "value",
        "EVENT_WRITE_WRAM_TEMPVAR": "addr",
    }
    for name in sorted(used_macros):
        match = re.fullmatch(r"EVENT_CHOOSE_RANDOM_SCRIPT_WORD_(\d+)", name)
        if not match:
            continue
        count = int(match.group(1))
        choice_args = [f"choice{i}" for i in range(count)]
        bodies[name] = [
            "    db $42",
            "    dl <target>",
            "    db <count>",
            *[f"    dw <choice{i}>" for i in range(count)],
        ]
        args[name] = ", ".join(["target", "count", *choice_args])
    for name in sorted(used_macros):
        match = re.fullmatch(r"EVENT_SWITCH_(JUMP|CALL)_TEMPVAR_(\d+)", name)
        if not match:
            continue
        opcode = "$10" if match.group(1) == "JUMP" else "$11"
        count = int(match.group(2))
        target_args = [f"target{i}" for i in range(count)]
        bodies[name] = [
            f"    db {opcode}, <count>",
            *[f"    dw <target{i}>" for i in range(count)],
        ]
        args[name] = ", ".join(["count", *target_args])
    missing = sorted(used_macros - bodies.keys())
    if missing:
        raise ValueError(f"missing macro definitions for: {', '.join(missing)}")
    lines = ["; Minimal macro vocabulary used by this source pilot."]
    for name in sorted(used_macros):
        lines.append(f"macro {name}({args.get(name, '')})")
        lines.extend(bodies[name])
        lines.append("endmacro")
        lines.append("")
    return lines


def render_source(
    rows: list[RowSource],
    labels: dict[str, str],
    names: dict[str, list[str]],
    *,
    family_id: str,
) -> tuple[str, dict[str, str]]:
    constants: dict[str, str] = {
        symbol: fmt_byte(value)
        for value, symbol in sorted(VAR_NAMES.items())
    }
    used_macros = {macro_name(instruction) for row in rows for instruction in row.instructions}

    rendered_rows: list[str] = []
    for row in rows:
        rendered_rows.append("")
        rendered_rows.append(f"org ${row.address.bank:02X}{row.address.offset:04X}")
        rendered_rows.append(f"{row.name}:")
        for instruction in row.instructions:
            label = labels.get(instruction.address.key)
            if label and label != row.name:
                rendered_rows.append(f"{label}:")
            rendered_rows.append(
                render_instruction(instruction, labels=labels, names=names, constants=constants)
            )

    constant_lines = ["; External constants and action-script variable slots."]
    for symbol, value in sorted(constants.items()):
        constant_lines.append(f"{symbol} = {value}")

    header = [
        "; Generated by tools/build_c3_event_script_source_pilot.py",
        f"; C3 event/actionscript source pilot: {family_id}.",
        "; This file is intentionally not wired into the bank C3 scaffold yet.",
        "hirom",
        "",
    ]
    source = "\n".join(header + constant_lines + [""] + macro_definitions(used_macros) + rendered_rows) + "\n"
    return source, constants


def row_manifest(row: RowSource) -> dict[str, Any]:
    return {
        "address": row.key,
        "name": row.name,
        "size": row.size,
        "sha1": hashlib.sha1(row.raw).hexdigest(),
        "instruction_count": len(row.instructions),
        "ends_at": f"C3:{row.address.offset + row.size:04X}",
    }


def render_report(
    rows: list[RowSource],
    *,
    family_id: str,
    description: str,
    next_step: str,
    output_path: Path,
    manifest_path: Path,
    mismatches: list[str],
) -> str:
    total_bytes = sum(row.size for row in rows)
    total_instructions = sum(len(row.instructions) for row in rows)
    validation = "PASS" if not mismatches else "FAIL"
    lines = [
        "# C3 event script source pilot",
        "",
        "## Summary",
        "",
        f"- Family: `{family_id}`.",
        f"- Source: `{output_path.relative_to(ROOT).as_posix()}`.",
        f"- Manifest: `{manifest_path.relative_to(ROOT).as_posix()}`.",
        f"- Spans emitted: {len(rows)}.",
        f"- Bytes represented: {total_bytes}.",
        f"- Instructions represented: {total_instructions}.",
        f"- ROM byte validation: {validation}.",
        "",
        description,
        "",
        "The source is not wired into `src/c3/bank_c3_helpers_asar.asm` yet. That is deliberate: this pass proves the representation and byte validation before replacing generated byte corridors in the bank scaffold.",
        "",
        "## Covered Spans",
        "",
        "| Address | Label | Bytes | Instructions |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(f"| `{row.key}` | `{row.name}` | {row.size} | {len(row.instructions)} |")
    lines.extend(
        [
            "",
            "## Validation",
            "",
        ]
    )
    if mismatches:
        for mismatch in mismatches:
            lines.append(f"- {mismatch}")
    else:
        lines.append("- Every emitted span was decoded over its exact byte range and revalidated against the ROM bytes used to generate it.")
    lines.extend(
        [
            "",
            "## Next Promotion Step",
            "",
            next_step,
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a C3 event/actionscript source-form pilot.")
    parser.add_argument("--rom", help="path to EarthBound (USA).sfc")
    parser.add_argument(
        "--family",
        choices=sorted(FAMILY_DEFAULTS),
        default=FAMILY_ID,
        help="script family to emit",
    )
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--index", type=Path, default=DEFAULT_REF_INDEX)
    parser.add_argument("--output", type=Path, help="override source output path")
    parser.add_argument("--report", type=Path, help="override markdown report path")
    parser.add_argument("--manifest", type=Path, help="override generated JSON manifest path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    family = FAMILY_DEFAULTS[args.family]
    source_map = args.source_map if args.source_map.is_absolute() else ROOT / args.source_map
    index_path = args.index if args.index.is_absolute() else ROOT / args.index
    default_output = family["output"]
    default_report = family["report"]
    default_manifest = family["manifest"]
    output_arg = args.output or default_output
    report_arg = args.report or default_report
    manifest_arg = args.manifest or default_manifest
    output_path = output_arg if output_arg.is_absolute() else ROOT / output_arg
    report_path = report_arg if report_arg.is_absolute() else ROOT / report_arg
    manifest_path = manifest_arg if manifest_arg.is_absolute() else ROOT / manifest_arg

    rom = load_rom(find_rom(args.rom))
    names = load_names(index_path)
    rows_by_address = load_row_map(source_map)
    rows = load_rows(rom, rows_by_address, list(family["rows"]), names)
    rows.extend(load_spans(rom, list(family["spans"]), names))
    labels = collect_label_map(rows, names)
    source, constants = render_source(rows, labels, names, family_id=args.family)

    mismatches: list[str] = []
    for row in rows:
        file_offset = hirom_to_file_offset(row.address.bank, row.address.offset, len(rom))
        expected = rom[file_offset : file_offset + row.size] if file_offset is not None else b""
        observed = b"".join(instruction.raw for instruction in row.instructions)
        if observed != expected:
            mismatches.append(f"{row.key}: decoded bytes do not match ROM span")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8")

    manifest = {
        "schema": "earthbound-decomp.c3-event-script-source-pilot.v1",
        "generated_by": "tools/build_c3_event_script_source_pilot.py",
        "family": args.family,
        "source": output_path.relative_to(ROOT).as_posix(),
        "report": report_path.relative_to(ROOT).as_posix(),
        "rows": [row_manifest(row) for row in rows],
        "constants": constants,
        "validation": {
            "mismatches": mismatches,
            "status": "pass" if not mismatches else "fail",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        render_report(
            rows,
            family_id=args.family,
            description=str(family["description"]),
            next_step=str(family["next"]),
            output_path=output_path,
            manifest_path=manifest_path,
            mismatches=mismatches,
        ),
        encoding="utf-8",
    )

    print(f"wrote {output_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {report_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {manifest_path.relative_to(ROOT).as_posix()}")
    print(f"rows={len(rows)} bytes={sum(row.size for row in rows)} validation={manifest['validation']['status']}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
