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

from decode_event_script import (
    ACTIONSCRIPT_ANIMATION_IDS,
    ACTIONSCRIPT_DIRECTION_WORDS,
    ACTIONSCRIPT_FIELD2B32_WORDS,
    CALL_ARG_COUNTS,
    CALL_TARGET_SEMANTICS,
    OPCODES,
    Address,
    Opcode,
    load_names,
    read_u16,
)
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
    "C3:0295": "RunVisualCountdownMoveReturn",
    "C3:02AC": "Event225_226_227_PoseTargetTracker",
    "C3:02C7": "LoopEvent225_226_227_PoseTargetTracker",
    "C3:02D7": "Event228_CoordinatePairYieldHalt",
    "C3:02EF": "Event229_CoordinatePairHalt",
    "C3:0303": "Event230_CoordinatePairHalt",
    "C3:0317": "Event231_CoordinatePairHalt",
    "C3:032B": "Event232_CoordinatePairHalt",
    "C3:033F": "Event228_232_CommonCoordinatePairMovement",
    "C3:036F": "Event233_PartyMemberPositionTextHalt",
    "C3:0394": "Event238_DoorCloseCoordinateRelease",
    "C3:03C0": "Event239_PartyMemberPositionTextHalt",
    "C3:03E5": "Event240_AreaAwarePartyFollowerLoop",
    "C3:03FD": "LoopEvent240_WaitUntilPlayerLeavesArea",
    "C3:0406": "Event240_CheckMovementBounds",
    "C3:0414": "Event240_CheckHorizontalTargetSide",
    "C3:0440": "Event240_MoveRightUntilBoundary",
    "C3:0467": "Event240_WaitAndRepeatBounds",
    "C3:046C": "Event240_ResetDirectionThenAreaLoop",
    "C3:0478": "Event241_FacingSequenceCoordinatePath",
    "C3:04FA": "Event242_PlayerDirectionTurnBiasRelease",
    "C3:0520": "Event243_ShortMovementRelease",
    "C3:053A": "Event243_AlternateShortMovementRelease",
    "C3:0550": "Event244_PairedMovementRelease",
    "C3:056E": "Event245_DirectionMovementRelease",
    "C3:0590": "Event246_MultiStepRouteRelease",
    "C3:059E": "LoopEvent246_WaitForMovementGate",
    "C3:05EF": "Event247_CollisionDisabledPresetMovement",
    "C3:061B": "Event248_CollisionDisabledPresetMovement",
    "C3:0647": "Event249_CollisionDisabledPresetMovement",
    "C3:0673": "Event250_CollisionDisabledPresetMovement",
    "C3:069F": "Event251_LeftOffsetVisualCountdownHalt",
    "C3:06BA": "Event252_RegistryAnchorVisualCountdownHalt",
    "C3:06DA": "Event253_JumpingVisualCountdownHalt",
    "C3:0704": "Event254_DirectionVisualCountdownHalt",
    "C3:084E": "LoopEarlyEvent255VisualCountdown",
    "C3:6E19": "Event605_FrameSelectorTaskAndRelease",
    "C3:6E41": "LoopVisualTypeFrameSelectorTask",
    "C3:6E45": "LoopUpdateVisualTypeFrameSelector",
    "C3:6E52": "Event607_OnettDoorCloseGateRandomWalk",
    "C3:6E5E": "Event608_OnettDoorCloseGateShortWander",
    "C3:6E6A": "Event609_OnettDoorCloseGateWideWander",
    "C3:6E76": "Event610_OnettDoorCloseGateFrameSelector",
    "C3:6E82": "Event611_PartyMemberCoordinateTextHalt",
    "C3:6EB7": "Event612_CoordinateTextHalt",
    "C3:6ED4": "Event613_VisualTypeTrackerLoop",
    "C3:6EF8": "LoopEvent613_TrackVisualTypePosition",
    "C3:6F08": "Event614_CoordinateTextHalt",
    "C3:6F33": "Event615_PartyMemberCoordinateTextHalt",
    "C3:6F68": "Event616_CoordinateTextHalt",
    "C3:6F85": "Event617_VisualTypeTrackerLoop",
    "C3:6FA9": "LoopEvent617_TrackVisualTypePosition",
    "C3:6FB9": "Event618_CoordinateTextHalt",
    "C3:6FE4": "Event619_PartyLookDoorSoundRelease",
    "C3:7010": "Event620_OnettDoorCloseArcWalkHalt",
    "C3:7098": "OnettDoorCloseReturnArcRelease",
    "C3:70A2": "RunOnettDoorCloseReturnArcPath",
    "C3:70FD": "OnettDoorCloseFlashWindowGfxHalt",
    "C3:715D": "OnettDoorClosePartyLookRetreatRelease",
    "C3:71F4": "OnettDoorCloseUseSharedDisplayReset",
    "C3:71FA": "OnettDoorClosePartyMemberDirectionHalt",
    "C3:7245": "OnettDoorCloseWalkInRelease",
    "C3:7276": "OnettDoorCloseDisplayResetLoop",
    "C3:7287": "OnettDoorCloseLiveAreaDisplayResetRelease",
    "C3:7296": "LoopOnettDoorCloseLiveAreaDisplayReset",
    "C3:72B0": "OnettDoorCloseRecurringWalkLoop",
    "C3:72D8": "LoopOnettDoorCloseRecurringWalkCycle",
    "C3:7377": "BounceOnettDoorCloseRecurringActor",
    "C3:73A8": "LoopOnettDoorCloseOverlapMovementQueue",
    "C3:73C2": "OnettDoorCloseFlashSoundHalt",
    "C3:7409": "OnettDoorCloseSharedMovementPrelude",
    "C3:7414": "LoopOnettDoorCloseSharedMovementRoute",
    "C3:1389": "Event311_TargetVisualTypePositionRelease",
    "C3:13A9": "Event312_PartyMemberOffsetRelease",
    "C3:13D5": "Event314_CoordinateRelease",
    "C3:13F7": "Event313_CoordinatePairRelease",
    "C3:141E": "Event315_SetPositionJumpDirectionCommon",
    "C3:1427": "Event316_DownwardTransitionRelease",
    "C3:1452": "Event317_WintersInputGateRelease",
    "C3:1476": "LoopEvent317_WaitForInputState",
    "C3:1485": "Event318_BubbleMonkeyLongRouteHalt",
    "C3:1529": "Event319_PartyMemberRouteTextHalt",
    "C3:1556": "Event320_BubbleMonkeyRouteRelease",
    "C3:155C": "Event321_BubbleMonkeyRouteTextRelease",
    "C3:1566": "RunEvent320_321_BubbleMonkeyReturnRoute",
    "C3:15CC": "Event322_WintersCoordinateRouteRelease",
    "C3:15F8": "Event323_WintersCoordinateRouteRelease",
    "C3:1626": "Event324_LoopingFacingPresentation",
    "C3:162F": "LoopEvent324_FacingPresentation",
    "C3:1651": "Event325_LoopingFacingPresentation",
    "C3:1667": "LoopEvent325_FacingPresentation",
    "C3:1689": "Event326_LoopingFacingPresentation",
    "C3:169F": "LoopEvent326_FacingPresentation",
    "C3:16BC": "Event327_WintersCoordinateRouteRelease",
    "C3:16E4": "Event328_WintersCoordinateRouteRelease",
    "C3:1717": "Event329_WintersShortCoordinateRouteRelease",
    "C3:1743": "Event330_WintersShortCoordinateRouteRelease",
    "C3:176F": "Event331_WintersShortCoordinateRouteRelease",
    "C3:179B": "Event332_WintersShortCoordinateRouteRelease",
    "C3:17C7": "Event333_WintersCoordinateRouteHalt",
    "C3:17FC": "Event334_WintersCoordinateRouteHalt",
    "C3:1831": "Event335_WintersAreaTextHalt",
    "C3:1869": "Event336_WintersVisualTypeRouteRelease",
    "C3:189A": "Event337_TrafficLightOffscreenRelease",
    "C3:18A5": "Event338_TransitionSnapshotMovementRelease",
    "C3:18D0": "Event339_TransitionSnapshotMovementRelease",
    "C3:18FD": "Event340_InputGatedBattleBgTransition",
    "C3:1931": "LoopEvent340_WaitForInputA",
    "C3:1957": "LoopEvent340_WaitForInputB",
    "C3:199E": "ContinueEvent340_BattleBgTransition",
    "C3:1A17": "Event340_BattleBgTransitionCancelReload",
    "C3:1A2E": "LoopEvent340_WaitForTempFlag1AfterReload",
    "C3:1A42": "Event341_WintersBattleBgExitRoute",
    "C3:1A83": "Event342_CameraRelativeCenterMoveHalt",
    "C3:1AB0": "Event342_Halt",
    "C3:1AB1": "Event343_CameraRelativeOffsetInitHalt",
    "C3:1ABD": "Event344_WintersCompassFacingRelease",
    "C3:1B14": "Event345_WintersRightwardMovementHalt",
    "C3:1B4B": "Event346_SanctuaryDisplaySequence",
    "C3:1BCA": "LoopEvent346_WaitForDirectionClass",
    "C3:1BD9": "LoopEvent346_RotateSanctuaryDisplayTask",
    "C3:1BED": "Event347_WintersBounceLoop",
    "C3:1BF0": "LoopEvent347_WintersBounce",
    "C3:1BFD": "Event350_LeftVisualCountdownRelease",
    "C3:1C23": "Event350_LeftwardVisualCountdownRelease",
    "C3:1C49": "Event351_SanctuaryDirectionPulseHalt",
    "C3:1C71": "LoopEvent351_WaitForDirectionClass",
    "C3:1C90": "LoopEvent351_DisplayLocationDirectionTask",
    "C3:1CA4": "Event352_SanctuaryPalettePulseRelease",
    "C3:1CAA": "LoopEvent352_PalettePulseForward",
    "C3:1CF4": "Event352_YieldRelease",
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
    "C3:5231": "WaitForCastScrollThreshold",
    "C3:5235": "LoopWaitForCastScrollThreshold",
    "C3:523F": "Event801_CastScrollSpawnSequence",
    "C3:1D2D": "LoopVar4TimedAnimationPulse",
    "C3:1D4A": "PauseThenRestartVar4AnimationPulse",
    "C3:1D4F": "InitVar4TimedAnimationPulseMovement",
    "C3:1D61": "Event355_CopyRegistryAnchorAndHalt",
    "C3:1D6A": "RunTStageBrightnessFadeDownTextRelease",
    "C3:1D89": "TStageRegistryAnchorMovementTextHalt",
    "C3:1DB5": "TStageTargetPoseMovementTextRelease",
    "C3:1DE2": "LoopWaitForTStageTargetPoseBrightnessTask",
    "C3:1DF4": "Event357_RegistryAnchorMovementPrep",
    "C3:1E0C": "LoopEvent357_WaitForBrightnessTask",
    "C3:1E14": "Event357_BrightnessFadeTask",
    "C3:1E2D": "InitPartyMemberMovementWithBrightnessTask",
    "C3:1E45": "LoopWaitForPartyMovementBrightnessTask",
    "C3:1E4D": "PartyMovementBrightnessFadeTask",
    "C3:1E66": "TStageRegistryUpRightVisualCountdownHalt",
    "C3:1E79": "TStageDownVisualCountdownHalt",
    "C3:1E7F": "TStageDownVisualCountdownCommonHalt",
    "C3:1E89": "TStageDownVisualCountdownRightHalt",
    "C3:1E92": "TStageVar4PulsePositionA",
    "C3:1E98": "TStageVar4PulsePositionCommonHalt",
    "C3:1EA6": "TStageVar4PulsePositionB",
    "C3:1EAF": "TStageVar4PulsePositionC",
    "C3:1EB8": "TStageVar4PulsePositionD",
    "C3:1EC1": "RunRightwardStepPulseHelper",
    "C3:1ED8": "RunLeftwardStepPulseHelper",
    "C3:2CD2": "LoopStageActorVerticalBounce",
    "C3:2E75": "TStage3LeftDanceRoute",
    "C3:3063": "TStage3RightDanceRoute",
    "C3:31ED": "TStage3FixedPositionVisualCountdownA",
    "C3:31F3": "TStage3FixedPositionVisualCountdownCommon",
    "C3:3205": "TStage3FixedPositionVisualCountdownB",
    "C3:320E": "TStage3FixedPositionVisualCountdownC",
    "C3:3217": "TStage3FixedPositionVisualCountdownD",
    "C3:3220": "TStage3FixedPositionVisualCountdownE",
    "C3:3229": "TStage3FixedPositionVisualCountdownF",
    "C3:3232": "TStage3ShortLeftStepReleaseA",
    "C3:324E": "TStage3ShortRightStepReleaseA",
    "C3:326A": "TStage3DiagonalStepReleaseA",
    "C3:3283": "TStage3LeftStepReleaseA",
    "C3:3299": "TStage3MultiStepReleaseA",
    "C3:32C1": "TStage3DoublePulseReleaseA",
    "C3:32D7": "TStage3CornerStepReleaseA",
    "C3:32FA": "TStage3SingleStepReleaseA",
    "C3:3310": "TStage3MultiLeftStepReleaseB",
    "C3:332C": "TStage3DoublePulseReleaseB",
    "C3:3342": "TStage3LongPulseReleaseB",
    "C3:335E": "TStage3CornerStepReleaseB",
    "C3:337D": "TStage3DualWindowDownHalt",
    "C3:3388": "TStage3DownVisualCountdownHalt",
    "C3:2CF0": "Event399_TStagePerformanceMovementRelease",
    "C3:2DFE": "Event401_TStage3VisualCountdownTextRelease",
    "C3:2E34": "Event437_TStage3PartyMovementTextRelease",
    "C3:2E56": "TStage3LeftVisualCountdownHalt",
    "C3:2E5F": "TStage3RightVisualCountdownHalt",
    "C3:2E68": "LoopTStage3FacingPulse",
    "C3:2E6F": "LoopTStage3FacingPulseBody",
    "C3:3399": "PulseDownFacingVisualCountdown",
    "C3:33AA": "PulseUpFacingVisualCountdown",
    "C3:33BB": "PulseLeftFacingVisualCountdown",
    "C3:33CC": "PulseRightFacingVisualCountdown",
    "C3:33DD": "RunStageFacingVisualPulsePattern",
    "C3:3424": "Event435_StagePerformancePulseRelease",
    "C3:34CF": "Event436_ObscuredStageSlideRelease",
    "C3:34FF": "Event438_StageVisualCountdownTextRelease",
    "C3:3535": "StagePositionVisualCountdownHalt",
    "C3:3549": "LoopVisualCountdownRandomWaitTask",
    "C3:3572": "Event440_FixedAnchorVisualFollowerA",
    "C3:3584": "LoopEvent440_CopyAnchorOffsetFollower",
    "C3:3595": "Event441_FixedAnchorVisualFollowerB",
    "C3:35A7": "LoopEvent441_CopyAnchorOffsetFollower",
    "C3:35B5": "Event442_TStageLongChoreographyRelease",
    "C3:3980": "Event443_TStageCrossMovementRelease",
    "C3:39D2": "Event444_TStageUpperRightRouteRelease",
    "C3:3A88": "Event446_TStageRightArcRelease",
    "C3:3AB5": "Event445_TStageLeftArcRelease",
    "C3:3AED": "Event447_VStage1TextRelease",
    "C3:3B0F": "Event448_PhotoSceneJumpRelease",
    "C3:3B77": "LoopPhotoSceneSpinDirectionTask",
    "C3:3B8B": "Event449_PhotoSceneRecordHalt",
    "C3:3B9E": "Event450_PhotoSceneCopyAnchorHalt",
    "C3:3BB2": "Event451_PhotoSceneCopyAnchorPriorityHalt",
    "C3:3BB7": "Event452_WindowGfxSoundRelease",
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
    "C3:3DD4": "Event479_ClearPoseFlagsAndPartyLookHalt",
    "C3:3E15": "LoopEvent479_WaitForMovementAndTempGate",
    "C3:3E24": "LoopEvent479_WaitForTaskCompletion",
    "C3:3E30": "TaskEvent479_ZBounceMarkComplete",
    "C3:3E42": "Event481_PartyMemberJumpFacingLoopHalt",
    "C3:3E72": "LoopEvent481_FacePartyMemberUntilGate",
    "C3:3E97": "LoopEvent481_WaitForPoseGate",
    "C3:3EA5": "LoopEvent481_FacePartyMember",
    "C3:3EB6": "TaskEvent481_CopyPartyAnchorYOffset",
    "C3:3EC4": "Event482_PartyMemberRouteAndFacingHalt",
    "C3:3EFF": "TaskEvent482_CoordinateRouteMarkComplete",
    "C3:3F4D": "LoopEvent482_WaitForMovementAndTempGate",
    "C3:3F5C": "LoopEvent482_WaitForTaskCompletion",
    "C3:3F68": "TaskEvent482_CopyPartyAnchorYOffset",
    "C3:3F76": "Event485_PartyMemberRouteRelease",
    "C3:3FC6": "LoopEvent485_WaitForMovement",
    "C3:3FE5": "Event486_RouteTextRelease",
    "C3:4014": "Event486_AlternatePartyLookJumpRelease",
    "C3:4025": "Event486_YieldRelease",
    "C3:4029": "RegistryAnchorPartyLookFlagRoute",
    "C3:4075": "SetYieldAndRegistryVisualFlags",
    "C3:4086": "LoopRegistryAnchorPoseOffset",
    "C3:40F0": "LoopTrafficLightAreaFlagToggle",
    "C3:410B": "TrafficLightFootprintAnchorA",
    "C3:4114": "TrafficLightFootprintAnchorB",
    "C3:411D": "TrafficLightFootprintAnchorC",
    "C3:4126": "TrafficLightFootprintAnchorD",
    "C3:412F": "TrafficLightFootprintAnchorE",
    "C3:4138": "PoseAnchorYOffsetMinus8Loop",
    "C3:414F": "LoopPoseAnchorYOffsetMinus8",
    "C3:415D": "PoseAnchorYOffsetPlus8Loop",
    "C3:4174": "LoopPoseAnchorYOffsetPlus8",
    "C3:4182": "PoseAnchorYOffsetPlus16Loop",
    "C3:4199": "LoopPoseAnchorYOffsetPlus16",
    "C3:41A7": "PoseAnchorYOffsetPlus32Loop",
    "C3:41BE": "LoopPoseAnchorYOffsetPlus32",
    "C3:41D1": "RandomCameraRelativePlacementRelease",
    "C3:41E9": "RunRandomCameraArcMovement",
    "C3:4233": "TaskWaitUntilPlayerAboveYThreshold",
    "C3:428F": "LoopRandomCameraTextWaitA",
    "C3:42D2": "LoopRandomCameraTextWaitB",
    "C3:430E": "RunRandomCameraVisualCountdownPulse",
    "C3:432A": "LoopRandomCameraVisualCountdownPulse",
    "C3:436D": "TaskRandomCameraTailOscillation",
    "C3:4373": "LoopRandomCameraTailOscillation",
    "C3:4392": "RunLeftwardBoundsReleasePath",
    "C3:43AE": "LoopWatchBoundsForLeftwardRelease",
    "C3:43C4": "CheckUpperBoundForLeftwardRelease",
    "C3:43D8": "ReleaseAfterLeftwardBoundsSatisfied",
    "C0:3F1E": "Apply_TransitionSnapshotToRegistryEntities",
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
    "C3:62C0": "RunCastScreenFacingPulseCycle",
    "C3:62E1": "Event826_CastScreenStepLoopRelease",
    "C3:6311": "Event827_CastScreenDirectionHalt",
    "C3:6320": "Event828_CastScreenLeftMoveRelease",
    "C3:6338": "Event829_CastScreenLeftMoveWaitOffscreenRelease",
    "C3:634A": "LoopEvent829_WaitUntilCastScreenOffscreen",
    "C3:6356": "CastScreenOrbitVectorDampingLoop",
    "C3:6384": "LoopCastScreenOrbitDamping",
    "C3:639E": "CastScreenFallRelease",
    "C3:63C6": "CastScreenFacingPulseUntilGone",
    "C3:63DC": "LoopCastScreenFacingPulseUntilGone",
    "C3:6405": "CastScreenHorizontalPatrolLoop",
    "C3:6408": "LoopCastScreenHorizontalPatrol",
    "C3:6447": "CastScreenBlinkHalt",
    "C3:6474": "CastScreenDirectionPulseHalt",
    "C3:64B1": "CastScreenLeftStepCycleLoop",
    "C3:64C3": "LoopCastScreenLeftStepCycleA",
    "C3:652A": "CastScreenFacingStepCycleLoop",
    "C3:653C": "LoopCastScreenFacingStepCycleB",
    "C3:65A3": "CastScreenStepCycleContinuation",
    "C3:65B5": "LoopCastScreenStepCycleContinuation",
    "C3:661C": "CastScreenDirectionHalt",
    "C3:6647": "CastScreenDirectionCycleHalt",
    "C3:6692": "CastScreenLeftRightHalt",
    "C3:66BF": "CastScreenSpawnPooRelease",
    "C3:66DC": "CastScreenStarMasterSpawnRelease",
    "C3:6707": "LoopCastScreenStarMasterArc",
    "C3:6726": "CastScreenVisualCountdownHalt",
    "C3:675D": "CastScreenBlinkUntilGoneRelease",
    "C3:6770": "LoopCastScreenBlinkUntilGone",
    "C3:678E": "CastScreenDownBlinkUntilGoneRelease",
    "C3:67A4": "CastScreenTendaSpawnRelease",
    "C3:67E6": "CastScreenTendaFacingHalt",
    "C3:6814": "CastScreenTendaRightStepHalt",
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
    "C3:0DCD": "Event287_SpaceTunnelFlagTextShakePath",
    "C3:0E21": "Event288_SpaceTunnelFaceTargetShakePath",
    "C3:0E52": "Event289_SpaceTunnelCoordinateTextPath",
    "C3:0E7F": "Event290_PartyMemberPositionTextHalt",
    "C3:0E99": "Event291_LeftFacingWaitRelease",
    "C3:0EB9": "Event292_SpaceTunnelTargetShakeRelease",
    "C3:0F20": "Event293_SpaceTunnelLongCoordinateTextHalt",
    "C3:0F9C": "Event294_SkyrunnerCrashCoordinatePath",
    "C3:1009": "Event294_SkyrunnerCrashContinue",
    "C3:1055": "LoopEvent294_SkyrunnerCrashBrightnessTask",
    "C3:1068": "Event295_SkyrunnerCrashPartyMemberTracker",
    "C3:1086": "Event295_UsePartyTrackerVisualProfile",
    "C3:109C": "LoopEvent295_WaitForPartyMemberArrival",
    "C3:10B1": "Event296_WintersCoordinatePath",
    "C3:1115": "Event297_LeftwardTransitionRelease",
    "C3:1140": "Event298_WintersTeleportCoordinatePath",
    "C3:1182": "Event299_CoordinateTextHalt",
    "C3:11B4": "Event300_DownwardTransitionRelease",
    "C3:11DF": "Event301_TempFlagDoorOpenPath",
    "C3:11FC": "LoopEvent301_WaitForTempFlag1Clear",
    "C3:1221": "Event302_DoorCloseCoordinatePath",
    "C3:126E": "Event303_TempFlagPartyMemberTracker",
    "C3:128B": "LoopEvent303_WaitForTempFlag2Clear",
    "C3:1296": "TrackPartyMemberFEAndVisualProfile",
    "C3:129E": "LoopEvent303_TrackPartyMemberFEUntilArrival",
    "C3:12AD": "Event304_PartyMemberFETrackerEntry",
    "C3:12C2": "Event305_DoorCloseMovementRelease",
    "C3:12E7": "Event306_TargetVisualTypeTrackerLoop",
    "C3:130B": "LoopEvent306_TargetVisualTypeUntilArrival",
    "C3:131B": "Event307_DownCoordinateRelease",
    "C3:133A": "Event308_CoordinateRelease",
    "C3:1359": "Event309_SetPositionCoordinateRelease",
    "C3:137E": "Event310_TrafficLightWaitShortcut",
    "C3:1831": "Event335_SpaceTunnel2StartTextHalt",
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
    "C3:6D18": "LoopWaitForUsableOverlapNeighborContext",
    "C3:6D21": "WaitBattleSwirlThenQueueVisualTypeMovement",
    "C3:6D29": "Event597_ArcMovementTargetRelease",
    "C3:6D40": "Event598_CityBusMovementDispatch",
    "C3:6D53": "Event599_600_CommonSpeedDispatch",
    "C3:6D62": "RunEvent599_600_CommonMovementDispatch",
    "C3:6D7B": "Event601_LeftFacingMovementDispatch",
    "C3:6D9F": "Event602_MovementDispatch",
    "C3:6DBE": "Event603_MovementDispatch",
    "C3:6DD9": "Event604_CoordinateChoiceTextRelease",
    "C3:6DF6": "Event604_AlternateCoordinateChoice",
    "C3:1EEF": "RunTStageDanceStepPattern",
    "C3:1FE8": "Event368_TStagePerformanceSequence",
    "C3:2138": "RunTStageAnimationStepPair",
    "C3:2149": "Event365_TStageLeftDanceSequence",
    "C3:22B3": "Event367_TStageLeftPartnerDanceSequence",
    "C3:2342": "Event366_TStageRightPartnerDanceSequence",
    "C3:23D1": "TStageLongPulseAndAnimationHalt",
    "C3:23F6": "LoopTStageLongAnimationPulse",
    "C3:240A": "Event371_TStageDualWindowPulseHalt",
    "C3:2454": "Event372_TStage2TextMovementRelease",
    "C3:2486": "TStage2TargetMovementTextRelease",
    "C3:24A8": "Event373_TStageDownVisualCountdownLeft",
    "C3:24B1": "Event374_TStageDownVisualCountdownRight",
    "C3:24BA": "TStageFixedPositionVisualCountdownHalt",
    "C3:24C0": "TStageFixedPositionVisualCountdownCommonHalt",
    "C3:24CE": "TStageFixedPositionVisualCountdownMiddle",
    "C3:24D7": "TStageFixedPositionVisualCountdownLeft",
    "C3:24E0": "Event378_407_TStageFixedPositionVisualCountdownRight",
    "C3:24E9": "Event379_408_TStageFixedPositionVisualCountdownCenter",
    "C3:24F2": "Event380_TStageDualWindowDownHaltAlias",
    "C3:24F9": "Event381_TStageDownVisualCountdownHalt",
    "C3:2507": "Event382_TStageDownWh0MaskHalt",
    "C3:2520": "Event383_TStageUpperLeftVisualCountdownHalt",
    "C3:2526": "TStageUpperVisualCountdownCommonHalt",
    "C3:2534": "Event385_TStagePerformanceUpperRoute",
    "C3:27AA": "Event397_TStagePerformanceUpperWh0Route",
    "C3:2818": "Event387_TStageLongIdleThenRelease",
    "C3:2860": "Event389_393_TStageShortIdleRelease",
    "C3:2878": "Event391_TStageRightFacingShortIdleRelease",
    "C3:2B9B": "Event398_TStagePerformanceUpperWh2Route",
    "C3:2C46": "Event388_TStageLongIdleLeftRelease",
    "C3:2C8A": "Event390_394_TStageShortIdleLeftRelease",
    "C3:2CA2": "Event392_TStageRightFacingShortIdleLeftRelease",
    "C3:2CBA": "TStageShortIdleLeftReleaseVariant",
    "C4:25F3": "ClearWh0HdmaChannel4EnableViaTrb",
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
    "C3:756D": "Event638_GumMachineCoordinateTextHalt",
    "C3:7A7C": "InitStationaryVar4PulseAndReturn",
    "C3:7A8A": "Event665_OffsetLeftMovementRelease",
    "C3:7AB5": "Event666_EscaperAppearMovementRelease",
    "C3:7B0B": "Event667_ThreedEscaperArcRiseRelease",
    "C3:7B2F": "LoopEvent667_ArcRiseDamping",
    "C3:7B5A": "ThreedEscaperTwoPointRelease",
    "C3:7B7E": "ThreedEscaperApproachTextHalt",
    "C3:7BB2": "ThreedEscaperApproachSecondLeg",
    "C3:7BDF": "ThreedEscaperApproachFinalLeg",
    "C3:7BFE": "Event670_ThreedEscaperLandingSequence",
    "C3:7CD8": "LoopEvent670_LandingFieldPulseTask",
    "C3:7CEA": "LoopEvent670_LandingAnimationPulseTask",
    "C3:7D33": "ThreedEscaperRandomTextCheck0",
    "C3:7D36": "LoopThreedEscaperRandomTextCheck0",
    "C3:7D84": "QueueThreedEscaperRandomText0",
    "C3:7D92": "ThreedEscaperRandomTextCheck1",
    "C3:7D95": "LoopThreedEscaperRandomTextCheck1",
    "C3:7DE3": "QueueThreedEscaperRandomText1",
    "C3:7DF1": "ThreedEscaperRandomTextCheck2",
    "C3:7DF4": "LoopThreedEscaperRandomTextCheck2",
    "C3:7E42": "QueueThreedEscaperRandomText2",
    "C3:7E50": "PrepareThreedEscaperRandomTextActor",
    "C3:7E66": "RunThreedEscaperRandomTextPause",
    "C3:7EAE": "TaskThreedEscaperRandomTextFacePlayer",
    "C3:7F1F": "TaskThreedEscaperRandomTextPartyLook",
    "C3:7F89": "RunThreedEscaperRandomTextPositionHelper",
    "C3:7FA5": "RunThreedEscaperRandomTextReleaseTail",
    "C3:7FCD": "RunThreedEscaperBounceAndRelease",
    "C3:80DE": "LoopThreedEscaperLiveAreaDirectionGateA",
    "C3:8106": "CheckThreedEscaperDirectionGateA",
    "C3:811A": "CheckThreedEscaperDirectionGateB",
    "C3:8135": "QueueThreedEscaperDirectionWaitA",
    "C3:8139": "ContinueThreedEscaperDirectionGateA",
    "C3:8164": "LoopThreedEscaperLiveAreaDirectionGateB",
    "C3:818C": "CheckThreedEscaperDirectionGateC",
    "C3:81A7": "QueueThreedEscaperDirectionWaitB",
    "C3:81AB": "ContinueThreedEscaperDirectionGateB",
    "C3:81C7": "LoopThreedEscaperFacingPulseFast",
    "C3:81EF": "LoopThreedEscaperFacingPulseSlow",
    "C3:8217": "LoopThreedEscaperFacingPulseMedium",
    "C4:9EC4": "RunFlyoverIntroTextSceneByIndex",
    "C3:83BC": "ChooseRandomFacingCycleStepCount",
    "C3:83D2": "Event693_LiveAreaFacingCycleFast",
    "C3:83E0": "LoopEvent693_LiveAreaFacingCycleFast",
    "C3:840A": "Event694_LiveAreaFacingCycleSlow",
    "C3:8418": "LoopEvent694_LiveAreaFacingCycleSlow",
    "C3:8442": "Event695_LongMovementPathYield",
    "C3:8515": "Event699_PartyFollowerLeftFacingHalt",
    "C3:852E": "LoopEvent699_PartyFollowerLeftFacingHalt",
    "C3:8531": "RefreshEvent699FollowerTargetPosition",
    "C3:8544": "Event700_MonotolyMovementTextSequence",
    "C3:85CA": "LoopEvent700_FinalShakeVisual",
    "C3:85D7": "LoopEvent700_FinalShake",
    "C3:85E2": "Event701_MonotolyMovementDialogueSequence",
    "C3:8678": "Event702_RightMovementDoorOpenHalt",
    "C3:868F": "Event703_BounceTextYieldHalt",
    "C3:86A9": "Event704_CollisionOffWaitRelease",
    "C3:86B2": "Event705_WindowGfxSequenceRelease",
    "C3:86FA": "Event706_WindowGfxSoundTextRelease",
    "C3:8751": "Event705_706_ColorMathFlashTask",
    "C3:8771": "Event707_HaemituFlagDirectionRelease",
    "C3:877A": "Event708_Letter1FlagDirectionRelease",
    "C3:8783": "Event709_Letter2FlagDirectionRelease",
    "C3:878C": "Event710_Letter3FlagDirectionRelease",
    "C3:8795": "Event707_710_CommonFlagDirectionRelease",
    "C3:879E": "Event707_710_UseUpDirection",
    "C3:87A1": "Event707_710_ApplyDirectionAndRelease",
    "C3:87B6": "Event712_AnimPortPokeyMovementHalt",
    "C3:88C3": "Event713_AnimPortPriorityBlinkPath",
    "C3:890F": "LoopEvent713_CopyPoseOffsetLeftUntilFlag",
    "C3:8928": "LoopEvent713_CopyPoseOffsetRight",
    "C3:8939": "Event714_AnimPortDualOffsetPath",
    "C3:8950": "LoopEvent714_CopyPoseOffsetRightUntilFlag",
    "C3:8967": "LoopEvent714_CopyPoseOffsetLeft",
    "C4:981F": "CopyStaticVisualBlock0be8To7c00",
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
    "C3:8992": "UseDirectionUpWhenVar4Clear",
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
    "C3:8EF1": "Event738_SetUpDirectionAndJumpCommon",
    "C3:8EF8": "Event739_SetLeftDirectionAndJumpCommon",
    "C3:8EFF": "Event740_SetRightDirectionAndJumpCommon",
    "C3:8F06": "Event737_740_CommonDirectionHalt",
    "C3:8F1B": "Event741_FacingPulseTextHalt",
    "C3:8F39": "Event742_TownHallMovementTextPath",
    "C3:8F86": "LoopEvent742_ReadText456Task",
    "C3:8F91": "Event743_TownHallMovementSoundPath",
    "C3:8FCE": "LoopReadText456And459Task",
    "C3:8FDF": "Event744_TownHallMovementTextPath",
    "C3:9022": "Event745_ReleaseCurrentVisualEntity",
    "C3:9025": "Event746_SetOnettTownHallPositionRelease",
    "C3:9030": "Event747_OffsetPoseDropTextPath",
    "C3:9053": "Event749_OffsetPoseDropHalt",
    "C3:9072": "Event755_FacingPulseHalt",
    "C3:9080": "Event756_DownRightMovementHalt",
    "C3:90B3": "Event748_RightThenLeftMovementHalt",
    "C3:90E6": "Event750_LongTownHallLoopTextPath",
    "C3:9155": "Event751_SetPositionMovementHalt",
    "C3:918A": "Event752_SetPositionMovementHalt",
    "C3:91AE": "Event753_SetPositionMovementHalt",
    "C3:91E3": "Event754_SetPositionTextYield",
    "C3:9213": "Event757_CoffeeTeaSwirlTextPath",
    "C3:9244": "LoopEvent757_StepBattleOverlayTask",
    "C3:9481": "LoopEvent764_RandomFacingTask",
    "C3:9ABB": "LoopBattleSwirlFootprintWaitInsideWindow",
    "C3:9AC7": "BattleSwirlFootprintSetup",
    "C2:654C": "RunMagicButterflyPpRestoreAnimation",
    "C2:EA15": "BeginBattleSwirlOverlayScript",
    "C2:EA74": "SwitchBattleSwirlOverlayToClosingScript",
    "C2:EACF": "WaitForBattleEffectStepReady",
    "C0:9FAE": "ActionScript_FadeInWrapper",
    "C0:A977": "Movement_LoadBattleBg",
    "C0:A9CF": "PrintCastNameEntityVar0_ReadThreeWords",
    "C0:A9EB": "PrintCastNameCurrentThreshold_ReadThreeWords",
    "C0:AA07": "ActionScript_FadeOutWithMosaic",
    "C0:A8B3": "Script_SetStagedPositionOffset_ReadTwoWords",
    "C0:A8F7": "ActionScript_PrepareNewEntityAtSelf",
    "C4:6E74": "CheckStagedPositionWithinPlayerProximityThreshold",
    "C4:8BDA": "AnimatedBackgroundCallback",
    "C4:9841": "BeginCoffeeTeaBattleBgVisualState",
    "C4:A7B0": "StepBattleOverlayScriptState",
    "C3:9AC7": "PrepareBattleSwirlFootprintVisualReturn",
    "C3:9AD9": "Event765_FlyoverIntroTextRelease",
    "C3:9AFA": "Event766_FlyoverPaletteTextRelease",
    "C3:9B25": "LoopEvent767_RandomMovementTask",
    "C3:9B48": "LoopEvent767_RandomDirectionMovement",
    "C3:9B86": "Event768_FlyoverPaletteFadeRelease",
    "C3:9CD7": "Event769_BounceVisualCountdownHalt",
    "C3:9D3D": "Event770_PartyLookCoordinateHalt",
    "C3:9D85": "Event771_AreaTextMovementHalt",
    "C3:9DCF": "Event772_CoordinateTextHalt",
    "C3:9E01": "WaitUntilNoBattleSwirlOrEnemyTouch",
    "C3:9E0E": "LoopWaitUntilBattleSwirlAndEnemyTouchClear",
    "C3:9E13": "Event773_DownDirectionOffscreenRelease",
    "C3:9E22": "Event774_CoordinateHalt",
    "C3:9E50": "Event775_BattleSwirlOverlayRelease",
    "C3:9E68": "LoopEvent775_WaitForBattleEffectStep",
    "C3:9E78": "Event775_DelayedOverlayTaskEnd",
    "C3:9E7B": "Event777_SetPendingInteractionsRelease",
    "C3:9E83": "Event778_ClearPendingInteractionsRelease",
    "C3:9E8B": "Event776_BattleSwirlWindowGfxRelease",
    "C3:9EB6": "Event779_LeftVisualCountdownHalt",
    "C3:9ECA": "Event780_DownVisualCountdownHalt",
    "C3:9EDE": "Event781_RegistrySlot2DownVisualCountdownHalt",
    "C3:9EF2": "Event782_PartyLyingDownSpawnRecovery",
    "C3:9F3F": "Event782_RunRecoveryColorPulseSequence",
    "C3:9F67": "Event782_DimFixedColorPulse",
    "C3:9F7A": "Event782_FadeFixedColorDown",
    "C3:9F8D": "Event782_FadeFixedColorUp",
    "C3:9FA0": "Event783_LyingDownBounceRelease",
    "C3:9FBA": "Event784_LeftRightWanderLoop",
    "C3:9FDB": "LoopEvent784_LeftRightWander",
    "C3:A2AA": "TrafficLightWaitUntilOffscreenAndRelease",
    "C3:A2B8": "Event8_Entry2WaitUntilOffscreenRelease",
    "C3:A2D3": "Event10_11_ReleaseCurrentVisualEntity",
    "C3:A2E4": "Event6_12_RandomDirectionWalk",
    "C3:A33B": "Event13_ShortRandomWander",
    "C3:A365": "Event16_WideRandomWander",
    "C3:A401": "InitNpcAttentionPathIfNoCachedNeighbor",
    "C3:A425": "ReturnFromNpcAttentionInit",
    "C3:A426": "StartNpcAttentionTerrainCollisionLoop",
    "C3:A42D": "StartNpcAttentionHorizontalCollisionLoop",
    "C3:A434": "LoopNpcAttentionTerrainCollision",
    "C3:A448": "LoopNpcAttentionHorizontalCollision",
    "C3:A45C": "FinishNpcAttentionAndReleaseActor",
    "C3:A48A": "RunNpcAttentionWideDistanceGate",
    "C3:A49A": "LoopNpcAttentionWideDistanceGate",
    "C3:A4AC": "RunNpcAttentionRoundWalkDirection",
    "C3:A4D9": "RunNpcAttentionRoundWalkReleaseLoop",
    "C3:A500": "LoopNpcAttentionRoundWalkDistanceGate",
    "C3:A507": "CheckNpcAttentionPlayerContext",
    "C3:A528": "RunNpcAttentionRoundWalkTowardPlayer",
    "C3:A553": "RunBusDriverAttentionReleaseLoop",
    "C3:A592": "PauseBusDriverAttentionNearPlayer",
    "C3:A59F": "LoopBusDriverAttentionDistanceGate",
    "C3:A5A6": "RunBusDriverAttentionRoundWalkDirection",
    "C3:A5D9": "LoopNpcAttentionCollisionTargetChase",
    "C3:A606": "RunNpcAttentionCollisionTargetRandomStep",
    "C3:A61F": "LoopNpcAttentionCollisionTargetFallbackGate",
    "C3:A626": "RunNpcAttentionCollisionTargetPlayerFallback",
    "C3:A643": "RunNpcAttentionHorizontalBounceChase",
    "C3:A656": "LoopNpcAttentionHorizontalBounceDistanceGate",
    "C3:A677": "RunNpcAttentionHorizontalBounce",
    "C3:A68D": "LoopNpcAttentionHorizontalBounceFallbackGate",
    "C3:A694": "RunNpcAttentionHorizontalBouncePlayerFallback",
    "C3:A6B1": "TaskNpcAttentionHorizontalBounce",
    "C3:A6C4": "RunNpcAttentionTightDistanceChase",
    "C3:A6D4": "LoopNpcAttentionTightDistanceWait",
    "C3:A6E0": "LoopNpcAttentionTightDistanceGate",
    "C3:A6F0": "LoopNpcAttentionTightDistanceFallbackGate",
    "C3:A6F7": "RunNpcAttentionTightDistancePlayerFallback",
    "C3:A714": "RunNpcAttentionWideDistanceBounceChase",
    "C3:A727": "LoopNpcAttentionWideDistanceBounceWait",
    "C3:A736": "LoopNpcAttentionWideDistanceBounceGate",
    "C3:A749": "LoopNpcAttentionWideDistanceFallbackGate",
    "C3:A750": "RunNpcAttentionWideDistancePlayerFallback",
    "C3:A76D": "TaskNpcAttentionSmallHorizontalBounce",
    "C3:A798": "LoopNpcAttentionArcDistanceGate",
    "C3:A7D1": "LoopNpcAttentionApproachPlayerTarget",
    "C3:A815": "LoopNpcAttentionArcPhaseGate",
    "C3:A830": "RunNpcAttentionArcPlayerVector",
    "C3:A83D": "LoopNpcAttentionArcRevectorGate",
    "C3:A851": "RunNpcAttentionArcTargetDirection",
    "C3:A884": "RunNpcAttentionTightArcDistanceRoute",
    "C3:A889": "LoopNpcAttentionTightArcDistanceGate",
    "C3:A8AC": "LoopNpcAttentionTightArcFallbackGate",
    "C3:A8B3": "RunNpcAttentionTightArcPlayerFallback",
    "C3:A8E6": "LoopNpcAttentionArcPlayerDistanceGate",
    "C3:A922": "RunNpcAttentionArcDistanceContinuation",
    "C3:A92B": "RunNpcAttentionWideGateArcRevector",
    "C3:A932": "RunNpcAttentionArcRevectorToPlayer",
    "C3:A966": "RunNpcAttentionArcDistanceRetry",
    "C3:A981": "LoopNpcAttentionArcVerticalBounce",
    "C3:A9A9": "LoopNpcAttentionArcRevectorGate",
    "C3:A9B7": "RunNpcAttentionArcTurnTowardPlayer",
    "C3:A9F3": "LoopNpcAttentionFinalWideDistanceGate",
    "C3:A9FF": "LoopNpcAttentionFinalPlayerRevectorGate",
    "C3:AA06": "RunNpcAttentionFinalArcRevector",
    "C3:A07F": "HaltBeforeEvent3CallbackPath",
    "C3:A080": "Event3_OverworldSnapshotSeedLoop",
    "C3:A090": "LoopEvent3_RefreshSnapshotCompanion",
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
    "C3:A272": "EndPreviousTaskThenDirectionFollowerPath",
    "C3:A27B": "LoopEvent4_CopyDirectionThenPause",
    "C3:A287": "Event7_DisplayResetAndRelease",
    "C3:A299": "Event9_TrafficLightProfileRefreshWait",
    "C3:A2AA": "TrafficLightWaitUntilOffscreenAndRelease",
    "C3:A2C6": "TrafficLightPulse16FrameRelease",
    "C3:A2D3": "TrafficLightFootprintPulse16FrameRelease",
    "C3:A2E4": "TrafficLightRandomDirectionLoop",
    "C3:A2FD": "LoopTrafficLightChooseRandomDirection",
    "C3:A33B": "TrafficLightRandomWander8x8",
    "C3:A349": "TrafficLightRandomWander16x16",
    "C3:A357": "TrafficLightRandomWander32x32",
    "C3:A365": "TrafficLightRandomWander24x8",
    "C3:A373": "TrafficLightRandomWander24x8Alt",
    "C3:A381": "TrafficLightRandomWanderPresetLoop",
    "C3:A3A1": "InitC40015PulseWithCollisionProbe",
    "C3:A3B7": "LoopRandomDirectionMovementWithRandomWait",
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
    "C3:ABED": "Event476_FlyoverScene0TextPath",
    "C3:AC27": "Event477_FlyoverScene1TextPath",
    "C3:AC61": "Event478_FlyoverScene2TextPath",
    "C3:ADAD": "LoopFlyoverPartyLeaderAnchorGate",
    "C3:ADBF": "ApplyFlyoverPartyLeaderFacingMode",
    "C3:ADC6": "RefreshFlyoverPartyLeaderOctantDirection",
    "C3:AE68": "LoopFlyoverBlinkTask",
    "C3:AEAC": "ContinueAfterTrafficLightWaitGate",
    "C3:AEB6": "LoopFlyoverSoundFacingPulse",
    "C3:A2FD": "LoopRandomDirectionMovementTimer",
    "C0:A8FF": "ActionScript_PrepareNewEntityAtPartyLeader",
    "C0:A912": "ActionScript_PrepareNewEntity",
    "C4:6A9A": "MapOctantToAltFacingQuadrant",
    "C4:8C2B": "CentreScreenOnEntityCallback",
    "C3:AFA3": "LoopPartyLooksAtActiveEntity",
    "C3:AFAC": "Event55_DogByeActiveAreaTextHalt",
    "C3:AFD8": "Event47_PartyMemberFEPositionTextHalt",
    "C3:AFFA": "Event48_PartyMemberFFThenFETextHalt",
    "C3:B021": "Event49_PartyMember09TrackerTextHalt",
    "C3:B03A": "LoopEvent49_WaitForPartyMember09Arrival",
    "C3:B04D": "Event53_SnapshotAnchorTextRelease",
    "C3:B0B6": "LoopField2B32VerticalOscillation",
    "C3:B0C7": "LoopField2B32OscillationDown",
    "C3:B0D8": "LoopField2B32OscillationUp",
    "C3:B0EC": "Event50_PartyMemberHopTextRelease",
    "C3:B135": "Event50_ZVelocityHopTask",
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
    "C3:BAEA": "Event91_TunnelGhostTeleportLeftRoute",
    "C3:BB06": "Event91_AlternateTeleportDestination",
    "C3:BB0B": "RunTunnelGhostTeleportRoute",
    "C3:BB17": "Event92_TunnelGhostTeleportWideRoute",
    "C3:BB2B": "Event92_TunnelGhostTeleportCommon",
    "C3:BB33": "Event99_TunnelGhostTeleportTextRoute",
    "C3:BB4C": "Event100_TunnelGhostTeleportWideRoute",
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
    "C3:C167": "Event473_PositionDoorCloseYieldSequence",
    "C3:C17A": "Event474_PositionDoorCloseRotateYieldSequence",
    "C3:C1A8": "Event475_PositionDoorCloseTargetPath",
    "C3:C1C7": "LoopEvent475_WaitForTargetPose",
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
    "C3:C4CF": "Event137_WintersRideLaunchTextPath",
    "C3:C506": "LoopWintersRideLaunchShake",
    "C3:C540": "Event138_WintersRideLaunchAltTextPath",
    "C3:C57A": "Event138B_RandomWanderLaunchHelper",
    "C3:C59A": "Event139_WintersCoordinateTextHalt",
    "C3:C5C6": "Event140_WintersRideInputWaitHalt",
    "C3:C5E5": "Event140_WintersRideInputTriggeredHalt",
    "C3:C5F0": "Event141_WintersRideCoordinateHalt",
    "C3:C60D": "Event142_WintersRidePartyLookCoordinateHalt",
    "C3:C634": "Event143_WintersRideLongMovementRelease",
    "C3:C687": "Event144_WintersRideMovementRelease",
    "C3:C6B5": "Event145_WintersRideVisualTypeRouteRelease",
    "C3:C6DD": "Event146_WintersRideLaunchArcRelease",
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
    "C3:CCB5": "Event161_SkyRunnerCrashLandingSequence",
    "C3:CDF0": "Event164_ObscuredSkyRunnerLandingHalt",
    "C3:CEA2": "LoopSpawnSkyRunnerElectricEffect",
    "C3:CEB9": "LoopSkyRunnerElectricEffectRise",
    "C3:CEC7": "Event163_SkyRunnerElectricEffectReflectRelease",
    "C3:CEF5": "Event166_SkyRunnerEffectFadeOutRelease",
    "C3:CF1B": "Event167_SkyRunnerEffectRiseTextHalt",
    "C3:CF3C": "Event168_VisualCountdownHalt",
    "C3:CF4B": "Event169_DownwardMoveTextRelease",
    "C3:CF76": "Event166_SkyRunnerFallFadeRelease",
    "C3:D04D": "Event167_SkyRunnerFallHalt",
    "C3:D0A4": "RunFourDirectionVisualCountdownReturn",
    "C3:D0C5": "Event172_DownFacingPositionWatchPath",
    "C3:D0D5": "LoopEvent172_WaitForC0C6B6Gate",
    "C3:D0E2": "LoopEvent172_PositionWatchGate",
    "C3:D0EE": "Event173_LeftFacingPositionWatchPath",
    "C3:D10E": "Event174_UpFacingPositionWatchPath",
    "C3:D12E": "Event175_LeftwardTextYieldPath",
    "C3:D159": "Event176_DownFacingMovementHalt",
    "C3:D172": "Event177_PartyPositionTextYieldHalt",
    "C3:D196": "Event178_PartyPositionNewEntityPath",
    "C3:D1C9": "Event180_FollowPartyVisualSlotLoop",
    "C3:D1E8": "LoopEvent180_FollowPartyVisualSlot",
    "C3:D1F8": "Event181_RideBusChaosTextNewEntity",
    "C3:D229": "Event182_BusPositionTextRelease",
    "C3:D251": "Event183_BusPositionTextRelease",
    "C3:D26E": "Event184_TonzuraBusTunnelRoute",
    "C3:D2F7": "Event185_TonzuraBusIntoThreed",
    "C3:D31D": "Event186_TonzuraBusTouchThreed",
    "C3:D395": "Event187_PartyMemberPositionTextPath",
    "C3:D3C8": "Event188_FollowPartyVisualSlotLoop",
    "C3:D3ED": "LoopEvent188_FollowPartyVisualSlot",
    "C3:D3FD": "Event189_TargetPositionRelease",
    "C3:D423": "Event190_RideBusDialogNewEntity",
    "C3:D464": "Event191_TargetPositionTextRelease",
    "C3:D486": "Event192_TonzuraBusRouteA",
    "C3:D4C9": "Event193_TonzuraBusRouteB",
    "C3:D4EF": "Event194_TonzuraBusRouteC",
    "C3:D515": "Event195_TonzuraBusRouteD",
    "C3:D53B": "Event196_TonzuraBusRouteE",
    "C3:D566": "Event197_TonzuraBusRouteF",
    "C3:D58C": "Event198_TonzuraBusRouteG",
    "C3:D5B2": "Event199_TonzuraBusRouteH",
    "C3:D5D8": "Event200_TonzuraBusTouchPath",
    "C3:D673": "Event201_BusStopBoardingTextPath",
    "C3:D6A0": "Event202_BusStopDialogNewEntity",
    "C3:D6D6": "Event203_BusStopRouteA",
    "C3:D732": "Event204_BusStopRouteB",
    "C3:D758": "Event205_BusStopLongRouteTextPath",
    "C3:D7E2": "Event206_BusStopBoardingTextPath",
    "C3:D806": "Event207_BusStopDialogNewEntity",
    "C3:D83C": "Event208_BusStopRouteA",
    "C3:D898": "Event209_BusStopRouteB",
    "C3:D8BE": "Event210_BusStopRouteC",
    "C3:D8E4": "Event211_BusStopRouteD",
    "C3:D913": "RunBusTunnelDesertRightTextHalt",
    "C3:D91C": "Event211_BusTunnelBridgeRightRoute",
    "C3:D966": "Event220_BusDesertTunnelRightRoute",
    "C3:D98C": "Event212_BusTunnelBridgeRightRoute",
    "C3:D9B2": "Event213_BusBridgeTunnelRightRoute",
    "C3:D9D8": "Event214_BusTunnelFoursideRoute",
    "C3:D9FE": "Event215_BusTouchFoursideRoute",
    "C3:DA49": "Event216_BusDesertTouchRoute",
    "C3:DA97": "Event217_BusTunnelDesertDriverLoop",
    "C3:DAE3": "LoopEvent217_BusTunnelDesertDriverDialog",
    "C3:DAF8": "Event218_BusTunnelHighwayLeftRoute",
    "C3:DB19": "Event219_BusBridgeHighwayLeftDriverLoop",
    "C3:DB65": "LoopEvent219_BusBridgeHighwayLeftDriverDialog",
    "C3:B431": "LoopWaitInsideLiveAreaThenRelease",
    "C3:B13E": "Event54_MeteoriteWindowColorPresentation",
    "C3:B1A6": "Event52_MeteoritePokeyHopTextHalt",
    "C3:B1C8": "LoopEvent52_WaitForTempFlag1Clear",
    "C3:B1E9": "Event53_MeteoritePokeyTextRelease",
    "C3:B208": "RunMeteoritePartyApproachPrelude",
    "C3:B241": "StartMeteoritePartyApproachRun",
    "C3:B2B4": "Event56_MeteoritePartyApproachTextRelease",
    "C3:B309": "Event57_MeteoritePartyApproachTextRelease",
    "C3:B347": "Event58_MeteoritePartyApproachTextRelease",
    "C3:B37F": "Event59_MeteoritePartyApproachTextRelease",
    "C3:B3D1": "Event60_MeteoritePartyApproachTextRelease",
    "C3:B445": "Event64_TwosonBusDriverMovementPath",
    "C3:B46F": "Event65_TwosonBusDriverDialogLoop",
    "C3:B490": "LoopEvent65_BusDriverDialog",
    "C3:B4A5": "Event66_BusToThreedTunnelRoute",
    "C3:B4FB": "Event67_BusReturnBranchRoute",
    "C3:B52A": "Event67_BusIntoThreedBranch",
    "C3:B538": "Event69_BusReturnTwosonRoute",
    "C3:B5D6": "Event68_BusReturnTwosonRouteA",
    "C3:B633": "Event70_TouchThreedRoute",
    "C3:B69C": "Event71_DownRightMovementTextPath",
    "C3:B6D4": "Event72_DownLeftMovementTextPath",
    "C3:DB7A": "RunBusTunnelBridgeRightTextHandoff",
    "C3:DBA0": "Event453_CopyPoseOffsetLeftUpPartyLookHalt",
    "C3:DBAC": "Event453_454_CommonPartyLookHalt",
    "C3:DBCC": "Event454_CopyPoseOffsetRightUpPartyLookHalt",
    "C3:DBDB": "CopyAnchorThenPrepareObscuredSimplePositionActor",
    "C3:DBE0": "PrepareObscuredSimplePositionActor",
    "C3:DBF2": "Event455_CoordinateMoveTextDriverLoop",
    "C3:DC42": "LoopEvent455_BusDriverDialog",
    "C3:DC57": "Event456_BusRouteTextHalt",
    "C3:DC74": "Event457_BusRouteTextHalt",
    "C3:DC91": "Event458_BusRouteTextHalt",
    "C3:DCAE": "Event459_BusRouteTextHalt",
    "C3:DCCB": "Event460_BusTransitionRouteRelease",
    "C3:DD15": "Event461_BusRouteTextHalt",
    "C3:DD32": "Event462_BusRouteTextHalt",
    "C3:DD4F": "Event463_CoordinateTextHalt",
    "C3:DD6C": "Event464_ObscuredRouteTransitionRelease",
    "C3:DE01": "Event455_BusDriverAttentionCoordinator",
    "C3:DE18": "LoopEvent455_BusDriverAttentionStateGate",
    "C3:DE24": "CheckEvent455_BusDriverWideDistanceGate",
    "C3:DE32": "SetEvent455_BusDriverAttentionActive",
    "C3:DE39": "LoopEvent455_BusDriverHorizontalWanderTask",
    "C3:DE43": "ChooseEvent455_BusDriverHorizontalWander",
    "C3:DE5E": "ChooseEvent455_BusDriverRightwardWander",
    "C3:DE6A": "QueueEvent455_BusDriverHorizontalWait",
    "C3:DE7B": "ChooseEvent455_BusDriverPlayerFacingRoute",
    "C3:DE94": "LoopEvent455_BusDriverIdleXTask",
    "C3:DE9C": "LoopEvent455_BusDriverVerticalWanderTask",
    "C3:DEA6": "ChooseEvent455_BusDriverVerticalWander",
    "C3:DEB8": "ChooseEvent455_BusDriverDownwardWander",
    "C3:DEBB": "QueueEvent455_BusDriverVerticalWait",
    "C3:DECC": "LoopEvent455_BusDriverPlayerYFacingRoute",
    "C3:DEE5": "LoopEvent455_BusDriverIdleYTask",
    "C3:DEED": "LoopEvent455_BusDriverTextHandoffTask",
    "C3:DF01": "FinishEvent455_BusDriverAttentionText",
    "C3:DF0A": "SaveEvent455_BusDriverAttentionPosition",
    "C3:DF1E": "Event34_MagicButterflyPpRestoreRelease",
    "C3:DF72": "BlinkAndRestoreSavedCoordinateState",
    "C3:DF90": "RunRightwardLiveAreaTextYieldPath",
    "C3:DF9F": "LoopWaitUntilCurrentSlotInsideLiveArea",
    "C3:DFB5": "LoopRandomBounceOrDownwardWaitTask",
    "C3:DFD4": "ChooseDownwardVelocityAndWaitTimer",
    "C3:DFE4": "ApplyRandomBounceWaitTimer",
    "C0:18F3": "ReloadMapAndResetPresentationState",
    "C0:A039": "PositionChangeCallback_C0A039",
    "C0:A055": "ProjectWorldToScreen_FromCamera39",
    "C0:A06C": "ProjectWorldToScreen_DirectCamera39Event",
    "C0:5E76": "UpdateCurrentSlotCollisionCache",
    "C0:8E9A": "GetRandom16",
    "C0:9451": "RestoreSavedCoordinateState",
    "C0:A82F": "DisableCurrentEntityCollision2",
    "C0:A838": "MarkCurrentSlotCollisionStateFFFF",
    "C0:A88D": "ActionScript_QueueTextPointer",
    "C0:A37A": "UpdatePosition_WhenNoNeighbor_WithSpriteRefresh_CurrentSlot",
    "C0:A480": "RefreshCurrentSlotVisualProfileFromLatchedKey",
    "C0:A4BF": "RefreshCurrentSlotVisualProfile_Mode0",
    "C0:A4A8": "RefreshCurrentSlotVisualProfile_Mode0IfAligned",
    "C0:A4B2": "RefreshCurrentSlotVisualProfile_Mode1IfAligned",
    "C0:A691": "GetCurrentSlotField2B32",
    "C0:A68B": "StoreAInCurrentSlotField2B32",
    "C0:A6A2": "Script_SetMovementStateCA4E",
    "C0:A6AD": "Script_SetMovementStateCBD3",
    "C0:A6D1": "MarkCurrentSlotCollisionState8000",
    "C0:A651": "Script_SetDirectionClassAndField1A86",
    "C0:9FF0": "PhysicsCallback_C09FF0",
    "C0:A0BB": "ProjectWorldToScreen_CopyWorld",
    "C0:9FA8": "ChooseRandomScriptByte",
    "C0:A65F": "SetCurrentSlotDirectionClassIfActive",
    "C0:A679": "Script_SetCurrentSlotDisplayControlBits",
    "C0:A841": "Script_PlaySoundEffectParameter",
    "C0:A864": "Script_CopyRegistrySlotAnchorToCurrentSlot_ReadByte",
    "C0:A87A": "Script_SetCameraRelativeAnchor_ReadTwoWords",
    "C0:A943": "ActionScript_GetPositionOfPartyMember",
    "C0:A8E7": "ScriptWrapper_C472A8_Mode0",
    "C0:9FC8": "Integrate_XYVelocityOnly",
    "C0:9FBB": "ActionScript_FadeOutWrapper",
    "C0:A98B": "ScriptWrapper_C46534_ReadThreeWords",
    "C0:A99F": "SpawnEntityRelative_ReadTwoWords",
    "C0:A9B3": "PrintCastNameParty_ReadThreeWords",
    "C0:A00C": "Integrate_XYAndZVelocity",
    "C0:A03A": "ProjectWorldToScreen_FromCamera31AndHeight",
    "C0:AA23": "ScriptWrapper_C47765_ReadThreeWords",
    "C0:AA6E": "Script_ApplyCurrentSlotVisualCountdownState",
    "C0:C353": "RefreshCurrentSlotProfileFromField2C9A_Current",
    "C0:C35D": "GetPlayerContext9885",
    "C0:C7DB": "UpdateCurrentSlotFootprintMask",
    "C0:D15C": "HasUsableOverlapNeighborContext",
    "C0:A6DA": "ClearCurrentEntityCollision",
    "C0:A6B8": "GetCurrentSlotHasNoCachedNeighborFlag",
    "C0:C4F7": "GetDirectionFromPlayerToEntity",
    "C0:C682": "RotateDirectionByCurrentSlotClass",
    "C0:D7F7": "Consume_CurrentSlotAttentionPath",
    "C0:D5B0": "Gate_NpcAttentionCoordinatorFromScript",
    "C0:D77F": "MarkOtherSlotsAttentionLocked",
    "C0:D7B3": "Save_CurrentSlotAttentionPosition",
    "C0:D7C7": "Restore_CurrentSlotAttentionPosition",
    "C0:D7E0": "Normalize_CurrentSlotAttentionState",
    "C0:D59B": "Check_NpcAttentionCoordinatorActive",
    "C0:6478": "Update_CurrentSlotNeighborCache_Priority",
    "C0:5E82": "Update_CurrentSlotCollisionCache_WithTerrainCompatibility",
    "C0:5ECE": "Update_CurrentSlotCollisionCache_FromHorizontalEdges",
    "C0:A360": "UpdatePosition_WhenNoNeighbor_WithSpriteRefresh",
    "C0:AACD": "ReturnX0002",
    "C0:AA3F": "Script_SetVisualSetupBytesByMode",
    "C0:AAAC": "Script_RefreshCurrentSlotVisualProfile",
    "C0:AAB5": "ScriptWrapper_C497C0_ReadWordByteByte",
    "C0:C83B": "InstallScriptMovementVectorFromDirection",
    "C0:CCCC": "InitializeArcMovementTargetState",
    "C0:CD50": "AdvanceArcMovementVectorFromPhase",
    "C0:CEBE": "TurnArcPhaseTowardTargetAngle",
    "C0:CF97": "FindNearbyCollisionMapTarget",
    "C0:D0D9": "TestCurrentSlotAgainstMovementTarget",
    "C0:D0E6": "TestCurrentSlotAgainstMovementTargetAlt",
    "C0:D195": "ClearCurrentSlotMovementVectorState",
    "C0:C48F": "GateWidePlayerDistanceBucket",
    "C0:C4AF": "GateTightPlayerDistanceBucket",
    "C0:C62B": "GetGatedEntityPositionDirectionFlag",
    "C4:23DC": "SetCenteredColorWindowRangePreset",
    "C4:240A": "SetFullscreenColorWindowRangePreset",
    "C4:248A": "StopWh0HdmaChannel4AndClearWhsel",
    "C4:24D1": "ApplyCenteredColorSubtractHalfPreset",
    "C4:257F": "ClearWh0HdmaChannel4Enable",
    "C4:258C": "ApplyDualCenteredColorSubtractHalfPreset",
    "C4:2624": "ClearWh2HdmaChannel5Enable",
    "C4:68A9": "ReadInputState006d",
    "C4:68AF": "ReadInputState0065",
    "C4:68B5": "TestValueLeftOfCurrentAnchorX",
    "C4:68DC": "TestValueAboveCurrentAnchorY",
    "C4:6903": "TestValueBelowPlayerY",
    "C4:6712": "SetLeadAndCompanionRegistryVisualFlags",
    "C4:675C": "ClearLeadAndCompanionRegistryVisualFlags",
    "C4:67B4": "RandomDelay0cTo2b",
    "C4:67C2": "RandomDelayBiasedByCurrentDrawY",
    "C4:67E6": "ClearFlagsForPose016fEntities",
    "C4:6A6E": "MapPlayerDirection987fToTurnBias",
    "C4:6B51": "RoundAngleToWalkDirectionStep",
    "C4:6B65": "SetCurrentSlotTargetToPlayerPosition",
    "C4:6ADB": "ComputeCurrentSlotTargetDirectionOctant",
    "C4:6B0A": "RoundAngleToOctantAndCacheCurrentSlot",
    "C4:6B2D": "FloorAngleToDirectionOctant",
    "C4:6C45": "SnapshotCurrentSlotAnchorToStagedPosition",
    "C4:6D23": "PlaceCurrentSlotAtRandomCameraXPlus70Y",
    "C4:6D4B": "PlaceCurrentSlotFromPhotoSceneRecord",
    "C4:7269": "ClassifyCurrentSlotAgainstAreaBounds",
    "C4:7499": "ApplyCurrentSlot0e5eBrightnessToPaletteRows",
    "C4:74A8": "ApplyCurrentSlot0e5eFixedColorMath",
    "C4:76A5": "StageCurrentEntityWh0MaskAndStartHdma",
    "C4:7705": "StageCurrentEntityWh2MaskAndStartHdma",
    "C4:7A27": "StageBaseSlotRelativeWh0BoxMask",
    "C4:7A6B": "MirrorCurrentEntityYAroundTarget1002",
    "C4:7A9E": "LoadCurrentEntityIndexedWindowGfxToVram",
    "C4:7B77": "LoadIndexedWindowGfxAndReadVariantByte",
    "C4:800B": "UndrawFlyoverTextAndRestoreWorldDisplay",
    "C4:880C": "InitEvent353MessageTileReveal",
    "C4:8A6D": "StepEvent353MessageTileReveal",
    "C4:8B3B": "MakePartyLookAtActiveEntity",
    "C4:8B2C": "SetTeleportEvent670LandingMode",
    "C4:978E": "CopyCgramShadow0200To4476",
    "C4:8BE1": "SimpleScreenPositionCallback",
    "C4:8C02": "SimpleScreenPositionCallbackOffset",
    "C4:8C2B": "CentreScreenOnEntityCallback",
    "C4:8C3E": "CentreScreenOnEntityCallbackOffset",
    "C4:DD28": "DecompressItoiProductionIntroAssets",
    "C4:DDD0": "DecompressNintendoPresentationIntroAssets",
    "C4:DE98": "InitializeYourSanctuaryDisplayState",
    "C4:DED0": "EnableYourSanctuaryDisplayBg2State",
    "C4:E2D7": "DisplayYourSanctuaryLocation",
    "C4:E4DA": "SetCastScrollThreshold",
    "C4:E4F9": "CheckCastScrollThreshold",
    "C4:E51E": "HandleCastScrolling",
    "C4:EC6E": "UploadSpecialCastPalette",
    "C4:ECE7": "IsEntityStillOnCastScreen",
    "C4:6E46": "SetYieldToTextLatch9641",
    "C4:681A": "QueueCurrentVisualTypeMovementScript",
    "C4:7044": "ProjectAngleIntoCurrentSlotVectorWords",
    "C4:733C": "DispatchCurrentLandingProfileAction",
    "C4:734C": "RefreshMapStripForIndexPreserveA",
    "C4:7369": "RefreshMapStripsAroundCameraFarWrapper",
    "C4:730E": "HalveCurrentSlot0d32PreserveSign",
    "C3:B06D": "Event51_PartyMemberOrbitLoop",
    "C3:B09B": "LoopEvent51_PartyMemberOrbitDamping",
    "EF:027D": "SeedOverworldEntitySnapshotCoordinates",
    "EF:031E": "RefreshOverworldEntitySnapshotState",
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

# Keep generated source-pilot callback labels in sync with the semantic audit.
for address, semantics in CALL_TARGET_SEMANTICS.items():
    LABEL_OVERRIDES[address] = semantics["name"]

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

def call_arg_fields(target_key: str) -> tuple[str, ...]:
    schema = CALL_TARGET_SEMANTICS.get(target_key, {}).get("args", "")
    return tuple(field.strip() for field in schema.split(",") if field.strip())


def call_arg_width(field: str) -> int | None:
    if field.endswith("_byte"):
        return 1
    if field.endswith("_word"):
        return 2
    if field.endswith("_long"):
        return 3
    return None


def callroutine_schema(target: Address, arg_count: int | None) -> tuple[str, ...] | None:
    fields = call_arg_fields(target.key)
    if not fields or any("[]" in field for field in fields):
        return None
    widths = [call_arg_width(field) for field in fields]
    if any(width is None for width in widths):
        return None
    if sum(int(width) for width in widths) != (arg_count or 0):
        return None
    return fields


def callroutine_schema_suffix(fields: tuple[str, ...]) -> str:
    parts = []
    for field in fields:
        base = re.sub(r"_(?:byte|word|long)$", "", field)
        text = re.sub(r"[^0-9A-Za-z_]+", "_", base)
        text = re.sub(r"_+", "_", text).strip("_")
        parts.append((text or "ARG").upper())
    return "_".join(parts)


CALLROUTINE_SCHEMA_MACROS: dict[str, tuple[str, ...]] = {}
for address, count in CALL_ARG_COUNTS.items():
    fields = call_arg_fields(address)
    if not fields or any("[]" in field for field in fields):
        continue
    widths = [call_arg_width(field) for field in fields]
    if any(width is None for width in widths):
        continue
    if sum(int(width) for width in widths) != count:
        continue
    CALLROUTINE_SCHEMA_MACROS[f"EVENT_CALLROUTINE_{callroutine_schema_suffix(fields)}"] = fields

DIRECTION_TEMPVAR_CONSUMERS = {
    "C0:A65F",  # SetCurrentSlotDirectionClassIfActive
    "C0:C83B",  # InstallScriptMovementVectorFromDirection
}

TEMPVAR_REPLACING_OPCODES = {
    "EVENT_WRITE_WORD_TEMPVAR",
    "EVENT_WRITE_WRAM_TEMPVAR",
    "EVENT_WRITE_VAR_TO_TEMPVAR",
    "EVENT_WRITE_TEMPVAR_WAITTIMER",
}

TEMPVAR_MUTATING_OPCODES = {
    "EVENT_BINOP_TEMPVAR",
    "EVENT_LOOP_TEMPVAR",
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
    "early-pose-coordinate-pair-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "early_pose_coordinate_pair_paths.asar.asm",
        "report": ROOT / "notes" / "c3-early-pose-coordinate-pair-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-early-pose-coordinate-pair-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:0295", "C3:036F", "EarlyPoseCoordinatePairPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers a compact early C3 terminal batch around ebsrc scripts 225-232: a visual-countdown movement return helper, a pose-target tracker shared by scripts 225-227, and coordinate-pair movement scripts 228-232 with their common movement tail.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the following `C3:036F..C3:098B` corridor should be split before the later `C4:6A6E` callback blocker.",
    },
    "early-party-look-coordinate-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "early_party_look_coordinate_paths.asar.asm",
        "report": ROOT / "notes" / "c3-early-party-look-coordinate-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-early-party-look-coordinate-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:036F", "C3:04FA", "EarlyPartyLookCoordinatePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers an early C3 terminal batch around ebsrc scripts 233-241: party-member position/text handoffs, a door-close coordinate release, an area-aware party-follower bounds loop, and a facing-sequence coordinate path before the later `C4:6A6E` callback blocker.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:04FA..C3:098B` corridor should be split around script boundaries before the `C4:6A6E` callback blocker.",
    },
    "early-turn-bias-and-coordinate-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "early_turn_bias_and_coordinate_routes.asar.asm",
        "report": ROOT / "notes" / "c3-early-turn-bias-and-coordinate-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-early-turn-bias-and-coordinate-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:04FA", "C3:069F", "EarlyTurnBiasAndCoordinateRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the no-argument `C4:6A6E` player-direction turn-bias helper. This covers ebsrc scripts 242-250: turn-bias setup, short movement releases, multi-step coordinate route handoffs, movement-finish waits, and collision-disabled preset movements before the later `C0:A838` callback blocker.",
        "next": "Continue only after pinning `C0:A838`, or move to another ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "early-visual-countdown-halts": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "early_visual_countdown_halts.asar.asm",
        "report": ROOT / "notes" / "c3-early-visual-countdown-halts-source-pilot.md",
        "manifest": ROOT / "build" / "c3-early-visual-countdown-halts-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:069F", "C3:0716", "EarlyVisualCountdownHalts"),
        ],
        "description": "High-ranked terminal source-pilot batch adjacent to the early turn-bias routes. This covers ebsrc scripts 251-254: left-offset and registry-anchor visual countdown halts, a short jumping visual-countdown halt, and a direction/profile visual-countdown halt before the `C0:A838` callback blocker.",
        "next": "Continue only after pinning `C0:A838`, or move to the next callback-contract seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "early-event255-pose-and-text-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "early_event255_pose_and_text_routes.asar.asm",
        "report": ROOT / "notes" / "c3-early-event255-pose-and-text-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-early-event255-pose-and-text-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:0716", "C3:08E5", "EarlyEvent255PoseAndTextRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C0:A838` collision-state entry point. This covers the early C3 event 255-style route cluster: event-flag gates, traffic-light/offscreen waits, fixed-coordinate text handoffs, party-look pose routing, and visual countdown setup before the later `C4:733C` callback.",
        "next": "Continue with the remaining `C3:08E5..C3:098B` early route tail after naming/pinning `C4:733C`, or move to another ready source-pilot seam.",
    },
    "early-event255-landing-profile-tail": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "early_event255_landing_profile_tail.asar.asm",
        "report": ROOT / "notes" / "c3-early-event255-landing-profile-tail-source-pilot.md",
        "manifest": ROOT / "build" / "c3-early-event255-landing-profile-tail-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:08E5", "C3:098B", "EarlyEvent255LandingProfileTail"),
        ],
        "description": "High-ranked source-pilot tail unlocked by the `C4:733C` landing-profile dispatch callback. This covers the post-countdown early C3 route tail: repeated movement-state pulses, sound setup, landing profile dispatch, and follow-up visual countdown/text handoffs into the shared `AA1E` helper.",
        "next": "Re-run the C3 frontier and continue with any remaining source-pilot gaps; this closes the formerly `C4:733C`-blocked early event 255 corridor.",
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
    "cast-scroll-event-801-spawn-sequence": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "cast_scroll_event_801_spawn_sequence.asar.asm",
        "report": ROOT / "notes" / "c3-cast-scroll-event-801-spawn-sequence-source-pilot.md",
        "manifest": ROOT / "build" / "c3-cast-scroll-event-801-spawn-sequence-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:5231", "C3:5F8B", "CastScrollEvent801SpawnSequence"),
        ],
        "description": "B-ranked full-gap source-pilot seam emitted after callback review. This covers ebsrc script 801's large cast-scroll setup/spawn sequence: repeated threshold waits, cast actor spawn wrappers, special cast palette uploads, cast-name/current-threshold helpers, and the final transition into the cast-screen actor refresh helpers.",
        "next": "The adjacent `C3:5F8B..C3:62C0` cast-member path family is already promoted; continue with one of the remaining callback-blocked C3 gaps from `notes/c3-source-pilot-frontier.md`.",
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
    "intro-cast-followup-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "intro_cast_followup_paths.asar.asm",
        "report": ROOT / "notes" / "c3-intro-cast-followup-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-intro-cast-followup-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:62C0", "C3:6356", "IntroCastFollowupPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the cast-screen facing pulse helper plus ebsrc scripts 826-829: small cast-screen step loops, direction setup halt/release paths, and a leftward movement path that waits until the actor leaves the cast-screen window.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:6356..C3:6834` continuation should be split before the later `C4:6B51` callback blocker.",
    },
    "cast-screen-orbit-continuation": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "cast_screen_orbit_continuation.asar.asm",
        "report": ROOT / "notes" / "c3-cast-screen-orbit-continuation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-cast-screen-orbit-continuation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6356", "C3:65A3", "CastScreenOrbitContinuation"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the angle/vector callback contracts. This covers the cast-screen orbit/damping and follow-up movement loops after the cast follow-up family: vector damping around cached targets, fall/release and facing pulse variants, horizontal patrols, blink/direction halts, and repeated step-cycle loops before the next cast-screen corridor.",
        "next": "Continue by splitting the adjacent `C3:65A3..C3:6834` cast-screen continuation, or move to another callback-unlocked frontier seam.",
    },
    "cast-screen-step-spawn-continuation": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "cast_screen_step_spawn_continuation.asar.asm",
        "report": ROOT / "notes" / "c3-cast-screen-step-spawn-continuation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-cast-screen-step-spawn-continuation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:65A3", "C3:6834", "CastScreenStepSpawnContinuation"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the preceding cast-screen orbit promotion. This covers the remaining cast-screen step/spawn continuation before the King spawn helper: directional step cycles, Poo/Star Master/Tenda spawn handoffs, visual-countdown and blink-until-offscreen loops, and compact halt variants.",
        "next": "Continue with another frontier seam; the cast-screen `C3:62C0..C3:6834` continuation is now source-backed.",
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
    "tunnel-ghost-teleport-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tunnel_ghost_teleport_routes.asar.asm",
        "report": ROOT / "notes" / "c3-tunnel-ghost-teleport-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tunnel-ghost-teleport-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:BAEA", "C3:BB5C", "TunnelGhostTeleportRoutes"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the two-word `C0:A87A` camera-relative anchor wrapper. This covers ebsrc scripts 91, 92, 99, and 100: tunnel ghost teleport-position setup, event-flag-dependent X offsets, teleport-destination entity preparation, shared movement setup, text-yield variants, and halt releases before the existing follower helper at `C3:BB5C`.",
        "next": "The adjacent `C3:BB5C..C3:BD03` tunnel-ghost follower family is already promoted; continue with another ready seam from `notes/c3-source-pilot-frontier.md`.",
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
    "boogy-city-bus-movement-dispatch": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "boogy_city_bus_movement_dispatch.asar.asm",
        "report": ROOT / "notes" / "c3-boogy-city-bus-movement-dispatch-source-pilot.md",
        "manifest": ROOT / "build" / "c3-boogy-city-bus-movement-dispatch-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6D29", "C3:6E41", "BoogyCityBusMovementDispatch"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C0:CCCC` movement-vector callback contract. This covers ebsrc scripts 597-606 after the Boogy Tent/city-bus paths: arc target setup, city-bus movement dispatchers, shared speed/profile movement branches, coordinate-choice text release, and the Dosei box frame-selector setup before the shared frame task at `C3:6E41`.",
        "next": "Continue with another callback-contract seam from `notes/c3-source-pilot-frontier.md`; the following Onett door-close gate family is already promoted.",
    },
    "onett-door-close-gate-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "onett_door_close_gate_paths.asar.asm",
        "report": ROOT / "notes" / "c3-onett-door-close-gate-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-onett-door-close-gate-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6E41", "C3:6F08", "OnettDoorCloseGatePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the visual-type frame-selector task plus ebsrc scripts 607-613: Onett door-close conditional gates, coordinate/text halt paths, and a visual-type tracking loop before script 614 at `C3:6F08`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:6F08..C3:7439` continuation should be split before the later `C4:6B51` callback blocker.",
    },
    "onett-door-close-coordinate-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "onett_door_close_coordinate_paths.asar.asm",
        "report": ROOT / "notes" / "c3-onett-door-close-coordinate-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-onett-door-close-coordinate-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:6F08", "C3:7010", "OnettDoorCloseCoordinatePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 614-619: chained coordinate/text halt paths, a second visual-type tracking loop, and a party-look door-sound release path before the `C4:6B51` callback blocker later in the corridor.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:7010..C3:7439` continuation should be split before the later `C4:6B51` callback blocker.",
    },
    "onett-door-close-arc-continuation": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "onett_door_close_arc_continuation.asar.asm",
        "report": ROOT / "notes" / "c3-onett-door-close-arc-continuation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-onett-door-close-arc-continuation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7010", "C3:7276", "OnettDoorCloseArcContinuation"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C4:6B51` and `C0:A8E7` callback contracts. This covers the Onett door-close arc-walk continuation around ebsrc script 620: multi-point movement arcs, angular vector rotation loops, fixed-color/window-gfx handoffs, party-look retreat movement, and short visual-countdown/direction halts before the next shared display-reset loop.",
        "next": "Continue by pinning `C4:730E` for the remaining angle/vector loops, or return to `C4:2624` for the adjacent theater-stage continuation blockers.",
    },
    "onett-door-close-display-continuation": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "onett_door_close_display_continuation.asar.asm",
        "report": ROOT / "notes" / "c3-onett-door-close-display-continuation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-onett-door-close-display-continuation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7276", "C3:7439", "OnettDoorCloseDisplayContinuation"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:6B51`/`C0:A8E7` arc continuation. This covers the follow-up Onett door-close display and movement continuations around ebsrc scripts 627 and neighbors: display reset loops, live-area release checks, recurring movement cycles, overlap-gated movement queueing, flash/sound halt, and the shared route prelude before `C3:7439`.",
        "next": "Continue with another callback contract from `notes/c3-source-pilot-frontier.md`; the Onett `C3:7010..C3:7439` corridor is now source-backed.",
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
    "bus-bridge-route-terminal-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bus_bridge_route_terminal_paths.asar.asm",
        "report": ROOT / "notes" / "c3-bus-bridge-route-terminal-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bus-bridge-route-terminal-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:DBF2", "C3:DD4F", "BusBridgeRouteTerminalPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 455-462: compact bus/bridge coordinate moves, recurring driver dialog loops, simple route text halts, and one transition snapshot release before the next bus route batch at `C3:DD4F`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:DD4F` continuation reaches a `C0:C48F` callback blocker around `C3:DE24` and should be split or pinned before promotion.",
    },
    "bus-bridge-obscured-route-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bus_bridge_obscured_route_paths.asar.asm",
        "report": ROOT / "notes" / "c3-bus-bridge-obscured-route-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bus-bridge-obscured-route-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:DD4F", "C3:DE01", "BusBridgeObscuredRoutePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 463-464: a compact coordinate/text halt and an obscured route transition sequence with display-control bit flips, a transition-snapshot handoff, and a short leftward movement before release.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:DE01..C3:DF90` continuation should be split before the `C0:C48F` callback blocker.",
    },
    "bus-driver-attention-coordinator": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bus_driver_attention_coordinator.asar.asm",
        "report": ROOT / "notes" / "c3-bus-driver-attention-coordinator-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bus-driver-attention-coordinator-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:DE01", "C3:DECC", "BusDriverAttentionCoordinator"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C0:C48F` wide-distance gate contract. This covers the first bus-driver attention coordinator continuation after the bridge/obscured route scripts: cached-neighbor setup, horizontal and vertical wander tasks, player-facing route selection, and the state gate that loops until the next Y-facing task body.",
        "next": "Continue only after pinning the next bus-driver callback blockers around `C0:D77F`, or move to another newly unlocked terminal seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "bus-driver-attention-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bus_driver_attention_release.asar.asm",
        "report": ROOT / "notes" / "c3-bus-driver-attention-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bus-driver-attention-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:DECC", "C3:DF1E", "BusDriverAttentionRelease"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C0:D77F/D7B3` NPC-attention cleanup contracts. This covers the bus-driver coordinator's Y-axis player-facing branch, attention cleanup, saved-position handoff into the shared battle-swirl/message helper, queued text pointer, and final visual release.",
        "next": "Continue only after pinning the later `C2:654C` callback blocker, or move to another small callback-blocked frontier seam.",
    },
    "magic-butterfly-pp-restore-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "magic_butterfly_pp_restore_release.asar.asm",
        "report": ROOT / "notes" / "c3-magic-butterfly-pp-restore-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-magic-butterfly-pp-restore-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:DF1E", "C3:DF90", "MagicButterflyPpRestoreRelease"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C2:654C` Magic Butterfly PP restore callback contract. This covers the Magic Butterfly restore/release path: projected jump setup, party-member target movement, PP restore animation call, yield/halt, and the final blink plus saved-coordinate restoration tail.",
        "next": "Continue with another callback-contract seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:DF90..` rightward live-area path family is already promoted.",
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
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:ABE0..C3:AFA3` flyover scene/wait corridor is now promoted.",
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
    "position-door-close-rotation-and-target-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "position_door_close_rotation_and_target_paths.asar.asm",
        "report": ROOT / "notes" / "c3-position-door-close-rotation-and-target-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-position-door-close-rotation-and-target-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C17A", "C3:C1E0", "PositionDoorCloseRotationAndTargetPaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the no-argument `C0:C682` direction-rotation helper. This covers ebsrc scripts 474-475 between the existing door-close yield sequence and helper paths: a four-step rotated-facing presentation, task cleanup, door-close sound helper handoff, target-position setup, party-look task launch, and target-pose wait loop.",
        "next": "The adjacent `C3:C1E0..C3:C227` position door-close helper family is already promoted; continue with another ready seam from `notes/c3-source-pilot-frontier.md`.",
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
    "winters-ride-launch-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winters_ride_launch_paths.asar.asm",
        "report": ROOT / "notes" / "c3-winters-ride-launch-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winters-ride-launch-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C4CF", "C3:C5C6", "WintersRideLaunchPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 137-139: Winters ride launch text setup, the shared launch shake loop, a random-wander launch helper, and a coordinate/text halt before script 140's `C4:68A9` callback blocker.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent script 140 at `C3:C5C6` needs the `C4:68A9` callback contract pinned before source promotion.",
    },
    "winters-ride-input-and-route-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winters_ride_input_and_route_release.asar.asm",
        "report": ROOT / "notes" / "c3-winters-ride-input-and-route-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winters-ride-input-and-route-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:C5C6", "C3:C810", "WintersRideInputAndRouteRelease"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:68A9` input-state callback contract. This covers ebsrc scripts 140-146: the Winters ride input wait/halt, triggered text halt, coordinate and party-look handoffs, long route release, visual-type route release, and launch arc release before the teleport-destination offset helpers.",
        "next": "Continue with another callback-contract seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:C810..C824` teleport offset helpers are already promoted.",
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
    "space-tunnel-crash-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "space_tunnel_crash_paths.asar.asm",
        "report": ROOT / "notes" / "c3-space-tunnel-crash-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-space-tunnel-crash-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:0DCD", "C3:1068", "SpaceTunnelCrashPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 287-294 plus the brightness task started by script 294: Space Tunnel flag/text handoffs, face-target shake paths, coordinate routes, Skyrunner crash movement, teleport destination writes, and a short palette-brightness task before ebsrc script 295 at `C3:1068`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:1068..C3:1460` corridor should be split around event-script boundaries before the later `C4:68A9` callback blocker.",
    },
    "skyrunner-crash-winter-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "skyrunner_crash_winter_paths.asar.asm",
        "report": ROOT / "notes" / "c3-skyrunner-crash-winter-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-skyrunner-crash-winter-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1068", "C3:126E", "SkyrunnerCrashWinterPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 295-302 after the Space Tunnel crash batch: Skyrunner crash party tracking, Winters coordinate movement, transition releases, teleport destination writes, temp-flag waits, and door open/close movement paths before ebsrc script 303 at `C3:126E`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:126E` continuation should be split before the later `C4:68A9` callback blocker.",
    },
    "party-member-tracker-winter-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_member_tracker_winter_paths.asar.asm",
        "report": ROOT / "notes" / "c3-party-member-tracker-winter-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-member-tracker-winter-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:126E", "C3:1389", "PartyMemberTrackerWinterPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 303-310: temp-flag party-member tracking, shared party-member/visual-type arrival loops, door-close movement release, compact Winters coordinate releases, and the traffic-light wait shortcut before the next corridor at `C3:1389`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:1389..C3:1460` continuation is the last local segment before the `C4:68A9` callback blocker.",
    },
    "winter-target-release-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winter_target_release_paths.asar.asm",
        "report": ROOT / "notes" / "c3-winter-target-release-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winter-target-release-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1389", "C3:1452", "WinterTargetReleasePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 311-316: target visual-type and party-member release paths, compact Winters coordinate releases, a jump through the direction-common helper, and a downward transition release before the `C4:68A9` callback blocker at `C3:1460`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:1452..C3:1D2D` corridor should be split and pinned around the `C4:68A9` callback contract.",
    },
    "winter-input-bubble-monkey-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winter_input_bubble_monkey_routes.asar.asm",
        "report": ROOT / "notes" / "c3-winter-input-bubble-monkey-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winter-input-bubble-monkey-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1452", "C3:15F8", "WinterInputBubbleMonkeyRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C4:68A9/C4:68AF` input-state callback contracts. This covers the Winters input-gated release, the long Bubble Monkey route halt, a party-member route/text halt, two Bubble Monkey route releases, their shared return route, and the next Winters coordinate route release.",
        "next": "Continue only after pinning the next callback blocker in the larger `C3:1452..C3:1D2D` corridor, or move to another small callback-contract seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "winter-coordinate-facing-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winter_coordinate_facing_routes.asar.asm",
        "report": ROOT / "notes" / "c3-winter-coordinate-facing-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winter-coordinate-facing-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:15F8", "C3:176F", "WinterCoordinateFacingRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch continuing the Winters/Bubble Monkey route corridor. This covers fixed coordinate releases, several looping facing-presentation helpers, and short Winters coordinate routes before the later callback-heavy continuation in the same map row.",
        "next": "Continue only after pinning the next callback blocker in the larger `C3:15F8..C3:1D2D` corridor, or move to another small callback-contract seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "winter-coordinate-transition-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winter_coordinate_transition_routes.asar.asm",
        "report": ROOT / "notes" / "c3-winter-coordinate-transition-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winter-coordinate-transition-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:176F", "C3:18D0", "WinterCoordinateTransitionRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch continuing the Winters route corridor. This covers more fixed-coordinate releases, two route halts, a Winters area text halt, a visual-type route release, a traffic-light offscreen release, and a transition-snapshot movement release.",
        "next": "Continue only after pinning the next callback blocker in the larger Winters corridor, or move to another small callback-contract seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "winter-input-battle-bg-transition": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winter_input_battle_bg_transition.asar.asm",
        "report": ROOT / "notes" / "c3-winter-input-battle-bg-transition-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winter-input-battle-bg-transition-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:18D0", "C3:199E", "WinterInputBattleBgTransition"),
        ],
        "description": "High-ranked terminal source-pilot batch continuing the Winters route corridor. This covers a transition-snapshot movement release plus an input-gated battle-background transition path with fade/mosaic setup, battle BG load, tick callback install, and repeated input waits before the next continuation.",
        "next": "Continue only after pinning the next callback blocker in the larger Winters corridor, or move to another small callback-contract seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "winter-battle-bg-reload-and-route-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winter_battle_bg_reload_and_route_release.asar.asm",
        "report": ROOT / "notes" / "c3-winter-battle-bg-reload-and-route-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winter-battle-bg-reload-and-route-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:199E", "C3:1B4B", "WinterBattleBgReloadAndRouteRelease"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the no-argument `C0:18F3` reload-map callback and the two-word `C0:A87A` camera-relative anchor wrapper. This covers the rest of ebsrc script 340's battle-background transition continuation plus scripts 341-345: reload branches, fade/tick callback cleanup, camera-relative actor setup, compass-facing presentation, and a rightward movement/text halt.",
        "next": "Continue only after pinning the next callback blocker in the larger Winters corridor, or move to another ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "winter-sanctuary-display-and-pulse-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "winter_sanctuary_display_and_pulse_release.asar.asm",
        "report": ROOT / "notes" / "c3-winter-sanctuary-display-and-pulse-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-winter-sanctuary-display-and-pulse-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1B4B", "C3:1CFB", "WinterSanctuaryDisplayAndPulseRelease"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the Your Sanctuary display helpers and the no-argument `C0:C682` direction-rotation helper. This covers ebsrc scripts 346, 347, 350, 351, and 352: Sanctuary display setup, display-location countdowns, rotating display task loops, bounce/visual-countdown releases, post-teleport callback setup, and palette pulse release.",
        "next": "Continue only after pinning the next callback blocker at `C3:1CFD`, or move to another ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "event353-message-tile-reveal": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "event353_message_tile_reveal.asar.asm",
        "report": ROOT / "notes" / "c3-event353-message-tile-reveal-source-pilot.md",
        "manifest": ROOT / "build" / "c3-event353-message-tile-reveal-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1CFB", "C3:1D2D", "Event353MessageTileReveal"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the no-argument `C4:880C`/`C4:8A6D` message-tile reveal helpers. This covers ebsrc script 353's animation setup, tile reveal initializer, stepped reveal loop, yield-to-text latch, and release into the shared visual-entity cleanup path.",
        "next": "The adjacent `C3:1D2D..C3:1EC1` stage brightness helpers are already promoted; continue with another ready seam from `notes/c3-source-pilot-frontier.md`.",
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
    "tstage-text-continuation-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_text_continuation_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-text-continuation-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-text-continuation-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:2DFE", "C3:2E75", "TStageTextContinuationPaths"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C4:74A8` fixed-color callback contract. This covers the theater-stage text continuation before the next `C4:2624` blocker: the TStage3 visual-countdown text release, party movement/text release, paired position halts, and a looping facing-pulse body.",
        "next": "Continue by pinning callback `C4:2624`; it blocks the adjacent stage-family continuation beginning at `C3:2E75`/`C3:2ED8` and other stage rows.",
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
    "stage-visual-continuation-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "stage_visual_continuation_paths.asar.asm",
        "report": ROOT / "notes" / "c3-stage-visual-continuation-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-stage-visual-continuation-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:34FF", "C3:3549", "StageVisualContinuationPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam unlocked by the `C4:74A8` fixed-color callback contract. This covers the adjacent stage visual-countdown continuation after the existing stage pulse path: registry-anchor setup, fixed-color callback application, movement wait, text release, and a fixed-position visual-countdown halt variant.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the next stage-family gaps are blocked on `C4:258C`, `C4:2624`, and other callback contracts.",
    },
    "stage-brightness-terminal-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "stage_brightness_terminal_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-stage-brightness-terminal-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-stage-brightness-terminal-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1D4F", "C3:1D6A", "StageBrightnessTerminalHelperA"),
            ("C3:1DF4", "C3:1E14", "StageBrightnessTerminalHelperB"),
            ("C3:1E2D", "C3:1E4D", "StageBrightnessTerminalHelperC"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers three small theater-stage terminal helpers around ebsrc scripts 355 and 357: var4 pulse initialization, registry-anchor halt, movement setup with center-screen tick callback, and brightness-task wait loops that stop before the `C4:74A8` color-math callback bodies.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent brightness task bodies should wait for the `C4:74A8` callback contract.",
    },
    "stage-brightness-continuation-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "stage_brightness_continuation_paths.asar.asm",
        "report": ROOT / "notes" / "c3-stage-brightness-continuation-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-stage-brightness-continuation-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1D6A", "C3:1DF4", "StageBrightnessTextMovementContinuations"),
            ("C3:1E14", "C3:1E2D", "StageBrightnessFadeDownTask"),
            ("C3:1E4D", "C3:1EC1", "StageBrightnessVisualCountdownContinuations"),
        ],
        "description": "High-ranked source-pilot frontier seam unlocked by the `C4:74A8` fixed-color callback contract. This covers the theater-stage brightness fade tasks and their adjacent movement/text paths, including registry-anchored stage movement, target-pose movement waits, and static visual-countdown halt variants.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent side-step pulse helpers are already promoted, and the remaining stage-family gaps now require new callback contracts.",
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
    "visual-countdown-anchor-followers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "visual_countdown_anchor_followers.asar.asm",
        "report": ROOT / "notes" / "c3-visual-countdown-anchor-followers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-visual-countdown-anchor-followers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:3549", "C3:35B5", "VisualCountdownAnchorFollowers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 440-441 plus their shared visual-countdown random-wait task: two fixed-coordinate actors start the countdown task, then continuously copy pose descriptor `$00A5` with small anchor-relative offsets.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent script 442 body should be split only after the `C4:258C` callback contract is pinned.",
    },
    "tstage-long-choreography-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_long_choreography_release.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-long-choreography-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-long-choreography-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:35B5", "C3:3980", "TStageLongChoreographyRelease"),
        ],
        "description": "B-ranked terminal source-pilot batch emitted after callback review. This covers ebsrc script 442: a long T-Stage choreography path with dual-window color setup, WH0 mask HDMA callback, repeated animation/facing pulses, timed yields, and a final release after clearing the channel-4 HDMA callback.",
        "next": "Continue with the adjacent stage/flyover corridor after pinning `C4:6D4B`, or move to another small callback-blocked frontier seam.",
    },
    "tstage-vstage-route-release-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_vstage_route_release_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-vstage-route-release-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-vstage-route-release-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:3980", "C3:3B0F", "TStageVStageRouteReleasePaths"),
        ],
        "description": "High-ranked terminal source-pilot batch emitted after the long T-Stage choreography path. This covers ebsrc scripts 443-447: T-Stage cross-stage movement, upper-right/left/right arc releases, and the V-Stage 1 text release before the photo-scene placement callback corridor.",
        "next": "Continue with the adjacent photo-scene setup scripts now that `C4:6D4B` is pinned, or move to another small callback-blocked frontier seam.",
    },
    "photo-scene-jump-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "photo_scene_jump_release.asar.asm",
        "report": ROOT / "notes" / "c3-photo-scene-jump-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-photo-scene-jump-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:3B0F", "C3:3B77", "PhotoSceneJumpRelease"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C4:6D4B` photo-scene placement contract. This covers ebsrc script 448's photo-scene jump/release setup: place current slot from the photo scene record, install camera/physics callbacks, launch the spin-direction task, perform the jump, face the selected party member, and release after the final yield.",
        "next": "Continue only after pinning `C0:C682` for the adjacent spin-direction task/body at `C3:3B77`, or choose another small callback-blocked frontier seam.",
    },
    "photo-scene-spin-and-window-gfx-release": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "photo_scene_spin_and_window_gfx_release.asar.asm",
        "report": ROOT / "notes" / "c3-photo-scene-spin-and-window-gfx-release-source-pilot.md",
        "manifest": ROOT / "build" / "c3-photo-scene-spin-and-window-gfx-release-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:3B77", "C3:3BFB", "PhotoSceneSpinAndWindowGfxRelease"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the no-argument `C0:C682` direction-rotation helper. This covers the photo-scene spin-direction task tail from ebsrc script 448, scripts 449-451's photo-scene record/copy-anchor halt variants, and script 452's window-gfx sound/release sequence before the existing window-gfx loader prologue.",
        "next": "The adjacent `C3:3BFB..C3:3C1D` window-gfx loader prologue is already promoted; continue with another ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "party-look-jump-and-route-terminal": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_look_jump_and_route_terminal.asar.asm",
        "report": ROOT / "notes" / "c3-party-look-jump-and-route-terminal-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-look-jump-and-route-terminal-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:3DD4", "C3:4029", "PartyLookJumpAndRouteTerminal"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the no-argument `C4:67E6` pose-flag clear helper. This covers ebsrc scripts 479, 481, 482, 485, and 486 after the party-look/window-gfx family: pose-flag cleanup, party-look-at active entity, Z-bounce task handoff, party-member facing loops, coordinate route tasks, and route/text release tails before the next C4 callback blocker.",
        "next": "Continue only after pinning callback `C4:6712` near `C3:4082`, or move to another ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "party-look-registry-visual-flag-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_look_registry_visual_flag_routes.asar.asm",
        "report": ROOT / "notes" / "c3-party-look-registry-visual-flag-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-look-registry-visual-flag-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4029", "C3:4138", "PartyLookRegistryVisualFlagRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by registry-visual-flag callback contracts. This covers the continuation after the party-look/window-gfx route family: registry-anchor pose tracking, yield/text latches, lead/companion visual flag setup/clear, and the fixed traffic-light footprint anchor variants before the next randomized movement helper.",
        "next": "Continue with the adjacent `C3:4138..C3:4392` route-tail corridor after deciding whether to pin the direct random helper at `C3:424B`, or move to another high-ranked source-pilot seam.",
    },
    "party-look-random-camera-route-tail": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_look_random_camera_route_tail.asar.asm",
        "report": ROOT / "notes" / "c3-party-look-random-camera-route-tail-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-look-random-camera-route-tail-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4138", "C3:4249", "PartyLookRandomCameraRouteTail"),
        ],
        "description": "High-ranked terminal source-pilot batch emitted after registry-visual-flag promotion. This covers the pose-anchor Y-offset loops, randomized camera-relative placement/release path, random arc movement helper, and the player-Y threshold wait task before the next direct RNG callback.",
        "next": "Continue with the remaining `C3:4249..C3:4392` route tail only after deciding whether direct `C0:8E9A` calls should be treated as event callback contracts, or move to the remaining NPC-attention frontier.",
    },
    "party-look-random-camera-text-tail": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_look_random_camera_text_tail.asar.asm",
        "report": ROOT / "notes" / "c3-party-look-random-camera-text-tail-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-look-random-camera-text-tail-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:4249", "C3:4392", "PartyLookRandomCameraTextTail"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by direct RNG callback coverage. This covers the remaining party-look/random-camera route tail: randomized delay placement, two input/text wait loops, projected visual countdown pulses, and the local movement task before the existing leftward-bounds release path.",
        "next": "The adjacent `C3:4392..C3:43DB` leftward-bounds release path is already promoted; continue with the next frontier from `notes/c3-source-pilot-frontier.md`.",
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
    "overworld-snapshot-seed-loop": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "overworld_snapshot_seed_loop.asar.asm",
        "report": ROOT / "notes" / "c3-overworld-snapshot-seed-loop-source-pilot.md",
        "manifest": ROOT / "build" / "c3-overworld-snapshot-seed-loop-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A080", "C3:A09F", "OverworldSnapshotSeedLoop"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the no-argument `EF:027D` overworld entity snapshot seed helper. This covers ebsrc script 3's snapshot setup loop: position-change and physics callback install, animation reset, snapshot coordinate seed, tick callback install, companion visual refresh polling, flag write, and halt.",
        "next": "The adjacent `C3:A09F..C3:A272` movement pulse and helper family is already promoted; continue with another ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "direction-follower-display-reset-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "direction_follower_display_reset_paths.asar.asm",
        "report": ROOT / "notes" / "c3-direction-follower-display-reset-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-direction-follower-display-reset-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A272", "C3:A299", "DirectionFollowerDisplayResetPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the compact ebsrc script 4/7 seam after the movement-vector helpers: an end-task handoff into a direction-following display loop, plus the event 7 visual/display reset release path before event 9's callback blocker.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:A299..C3:A401` should be split after the `C0:C353` callback contract is pinned.",
    },
    "traffic-light-profile-and-random-wander": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "traffic_light_profile_and_random_wander.asar.asm",
        "report": ROOT / "notes" / "c3-traffic-light-profile-and-random-wander-source-pilot.md",
        "manifest": ROOT / "build" / "c3-traffic-light-profile-and-random-wander-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A299", "C3:A401", "TrafficLightProfileAndRandomWander"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the no-argument `C0:C353` current-slot profile refresh contract. This covers ebsrc scripts 9-18: traffic-light/offscreen release variants, footprint/profile refresh setup, random direction selection, collision-probe tasks, and size-specific random-wander presets before the shared NPC attention path helper.",
        "next": "The adjacent `C3:A401..C3:A48A` NPC attention helper family is already promoted; continue with another ready seam from `notes/c3-source-pilot-frontier.md`.",
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
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:756D..C3:7A7C` gum-machine/flyover corridor is now promoted.",
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
    "sky-runner-electric-effect-release-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "sky_runner_electric_effect_release_paths.asar.asm",
        "report": ROOT / "notes" / "c3-sky-runner-electric-effect-release-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-sky-runner-electric-effect-release-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:CEC7", "C3:CF76", "SkyRunnerElectricEffectReleasePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 163 and 166-169: Sky Runner electric-effect reflect/release, rising/fade-out effect handoffs, visual-countdown halt, and a short downward movement/text release path before the next callback-heavy continuation.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:CF76..C3:D0A4` continuation should be split before the later `C4:74A8` callback blocker.",
    },
    "sky-runner-landing-sequence-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "sky_runner_landing_sequence_paths.asar.asm",
        "report": ROOT / "notes" / "c3-sky-runner-landing-sequence-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-sky-runner-landing-sequence-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:CCB5", "C3:CEA2", "SkyRunnerLandingSequencePaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:74A8` fixed-color callback contract. This covers ebsrc scripts 161 and 164: Sky Runner landing/crash movement routing, electric-effect task handoffs, window-gfx/flyover text restoration, and the obscured landing halt variant.",
        "next": "Continue with another newly unlocked seam from `notes/c3-source-pilot-frontier.md`; the adjacent electric-effect helper/release families are already promoted, and `C3:CF76..C3:D0A4` is now ready.",
    },
    "sky-runner-fall-handoff-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "sky_runner_fall_handoff_paths.asar.asm",
        "report": ROOT / "notes" / "c3-sky-runner-fall-handoff-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-sky-runner-fall-handoff-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:CF76", "C3:D0A4", "SkyRunnerFallHandoffPaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:74A8` fixed-color callback contract. This covers the Sky Runner fall/fade continuation in ebsrc scripts 166-167: flyover text restoration, falling animation handoff, entity spawn, and the alternate halt path.",
        "next": "Continue with another newly unlocked seam from `notes/c3-source-pilot-frontier.md`; good small follow-ups include `C3:1D6A..C3:1DF4`, `C3:1E4D..C3:1EC1`, and `C3:34FF..C3:3549`.",
    },
    "small-terminal-helper-cleanup": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "small_terminal_helper_cleanup.asar.asm",
        "report": ROOT / "notes" / "c3-small-terminal-helper-cleanup-source-pilot.md",
        "manifest": ROOT / "build" / "c3-small-terminal-helper-cleanup-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:0C55", "C3:0C67", "SmallMovementPresetField2B32RefreshHelper"),
            ("C3:2138", "C3:2149", "TStageAnimationStepPair"),
            ("C3:3399", "C3:33DD", "FacingVisualCountdownPulseHelpers"),
            ("C3:6D18", "C3:6D29", "QueueVisualTypeMovementAfterOverlapWait"),
            ("C3:A07F", "C3:A080", "HaltBeforeEvent3CallbackPath"),
            ("C3:6A3E", "C3:6A41", "CastPathReleaseTail"),
            ("C3:A209", "C3:A20E", "DelayThenReleaseHelper"),
            ("C3:A271", "C3:A272", "EndTaskHelper"),
            ("C3:BAD7", "C3:BAEA", "TunnelGhostThreedWarpTextHalt"),
            ("C3:C167", "C3:C17A", "PositionDoorCloseYieldSequence"),
        ],
        "description": "High-ranked source-pilot frontier cleanup emitted as labeled event/actionscript macro assembly. This covers compact terminal helpers from the ready frontier: a movement preset/field refresh helper, a T-Stage animation step pair, four one-shot facing visual countdown pulses, a Boogy Tent visual-type movement queue task, a single-byte halt before event 3's callback path, a cast-path release tail, the four-frame delay release helper, a single-byte end-task helper, a tunnel ghost Threed warp text halt, and a position door-close yield sequence.",
        "next": "Continue by pinning callback contracts from `notes/c3-source-pilot-frontier.md`; the cheap ready terminal crumbs are now represented as source-form pilots.",
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
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:8515..C3:86B2` Monotoly corridor is now promoted, while `C3:86B2..C3:8978` remains a separate follow-up.",
    },
    "monotoly-coordinate-text-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "monotoly_coordinate_text_paths.asar.asm",
        "report": ROOT / "notes" / "c3-monotoly-coordinate-text-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-monotoly-coordinate-text-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:8515", "C3:86B2", "MonotolyCoordinateTextPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 699-704: a party-follower facing halt, Monotoly movement/dialogue sequences, a rightward door-open movement halt, a bounce/text-yield halt, and the collision-off wait/release path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:86B2..C3:8978` continuation begins with script 705 and should be split separately.",
    },
    "window-gfx-sequence-release-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "window_gfx_sequence_release_paths.asar.asm",
        "report": ROOT / "notes" / "c3-window-gfx-sequence-release-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-window-gfx-sequence-release-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:86B2", "C3:8751", "WindowGfxSequenceReleasePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 705-706: window-gfx variant loading sequences, a color-math flash task start, sound/text handoffs, and flyover-text undraw/restore release paths before the shared `C3:8751` flash task callback blocker.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:8751..C3:8978` continuation is blocked on the `C4:74A8` color-math callback contract.",
    },
    "anim-port-flag-pokey-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "anim_port_flag_pokey_paths.asar.asm",
        "report": ROOT / "notes" / "c3-anim-port-flag-pokey-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-anim-port-flag-pokey-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:8751", "C3:8978", "AnimPortFlagPokeyPaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:74A8` fixed-color callback contract. This covers ebsrc scripts 707-714: the animation-port brightness flash task, flag-gated direction release variants, the Pokey movement/text halt, and dual pose-offset animation-port paths before the existing direction-task family.",
        "next": "Continue with another newly unlocked seam from `notes/c3-source-pilot-frontier.md`; `C3:CCB5..C3:CEA2`, `C3:CF76..C3:D0A4`, and `C3:9EF2..C3:9FF2` are now full-gap candidates.",
    },
    "tstage-dance-sequence-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_dance_sequence_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-dance-sequence-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-dance-sequence-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:1EEF", "C3:2138", "TStageDanceSequencePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the ebsrc T-Stage dance helper, script 368's staged performance sequence, and the paired animation-step helper at `C3:2138`.",
        "next": "Continue with the adjacent `C3:2138..C3:2CD2` stage-performance corridor after pinning the `C4:2624` channel-5 HDMA disable contract, or take another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "tstage-dance-followup-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_dance_followup_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-dance-followup-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-dance-followup-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:2149", "C3:240A", "TStageDanceFollowupPaths"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the channel-5/channel-4 HDMA disable contracts. This covers ebsrc scripts 365-367 and a compact follow-up halt: T-Stage dance movements, partner left/right mirrored dance loops, WH2/WH0 HDMA teardown, and the long pulse-and-animation hold before the next dual-window color callback.",
        "next": "Continue with the adjacent `C3:240A..C3:2CD2` stage-performance corridor after the `C4:258C` dual-window color callback contract is pinned, or take another ready seam from `notes/c3-source-pilot-frontier.md`.",
    },
    "tstage-dual-window-position-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_dual_window_position_paths.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-dual-window-position-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-dual-window-position-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:240A", "C3:24E0", "TStageDualWindowPositionPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam unlocked by the dual-window color callback contract. This covers ebsrc script 371's dual-window pulse halt, a T-Stage text movement release with center-screen tracking, and nearby fixed-position visual-countdown halt entries that reuse the existing stage countdown helper.",
        "next": "Continue with another ready seam from `notes/c3-source-pilot-frontier.md`; after this promotion the larger `C3:24E0..C3:2CD2` stage corridor still benefits from a split around its local actor scripts and the vertical-bounce task.",
    },
    "tstage-performance-upper-corridor": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage_performance_upper_corridor.asar.asm",
        "report": ROOT / "notes" / "c3-tstage-performance-upper-corridor-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage-performance-upper-corridor-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:24E0", "C3:2CD2", "TStagePerformanceUpperCorridor"),
        ],
        "description": "B-ranked but fully decodable stage corridor emitted after review. This covers ebsrc scripts 378-398 and shared helper entries: fixed-position countdown aliases, upper-stage visual countdown halts, long T-Stage performance routes using WH0/WH2 HDMA mask callbacks, and left/right mirrored idle release variants before the vertical-bounce task at `C3:2CD2`.",
        "next": "Continue with the now-neighboring stage gap `C3:2E75..C3:3399` or inspect the remaining callback-blocked C3 frontiers for cheap zero-operand helpers.",
    },
    "tstage3-performance-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "tstage3_performance_routes.asar.asm",
        "report": ROOT / "notes" / "c3-tstage3-performance-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-tstage3-performance-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:2E75", "C3:3399", "TStage3PerformanceRoutes"),
        ],
        "description": "B-ranked but fully decodable stage corridor emitted after review. This covers the mirrored T-Stage 3 performance routes, WH2/WH0 HDMA mask teardown, centered color-window handoffs, staged facing pulses, and compact fixed-position visual-countdown release variants leading into the shared facing-pulse helpers at `C3:3399`.",
        "next": "Continue with another B-ranked fully decodable stage seam or inspect the remaining callback-blocked C3 frontiers for small zero-operand helper contracts.",
    },
    "gum-machine-flyover-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "gum_machine_flyover_paths.asar.asm",
        "report": ROOT / "notes" / "c3-gum-machine-flyover-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-gum-machine-flyover-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:756D", "C3:7A7C", "GumMachineFlyoverPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the `C3:7559` continuation around ebsrc scripts 638-654, including coordinate/text-yield movement paths, flyover intro text scene dispatches using a tempvar scene index, randomized movement helpers, and nearby release or text-halt tails.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:7A7C..C3:835D` remains a larger corridor and should be split around its local helper/script boundaries.",
    },
    "threed-escaper-appear-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "threed_escaper_appear_paths.asar.asm",
        "report": ROOT / "notes" / "c3-threed-escaper-appear-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-threed-escaper-appear-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7A7C", "C3:7B0B", "ThreedEscaperAppearPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the stationary var4 pulse helper plus ebsrc scripts 665-666: an offset-left movement release and the Threed escaper-appear gate that waits for the player to leave the active area, writes the appearance flag, and walks through two coordinates before release.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:7B0B..C3:835D` continuation starts at script 667 and should be split before the later `C4:6B51` callback blocker.",
    },
    "threed-escaper-arc-continuation": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "threed_escaper_arc_continuation.asar.asm",
        "report": ROOT / "notes" / "c3-threed-escaper-arc-continuation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-threed-escaper-arc-continuation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7B0B", "C3:7BFE", "ThreedEscaperArcContinuation"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the angle/vector callback contracts. This covers ebsrc script 667 and nearby Threed escaper continuations: the rising arc damping loop, two-point release path, proximity-checked approach legs, and the text halt before the next callback-heavy continuation.",
        "next": "Continue with the adjacent `C3:7BFE..C3:835D` region after pinning the next callback blocker (`C4:8B2C`), or take another frontier seam.",
    },
    "threed-escaper-landing-continuation": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "threed_escaper_landing_continuation.asar.asm",
        "report": ROOT / "notes" / "c3-threed-escaper-landing-continuation-source-pilot.md",
        "manifest": ROOT / "build" / "c3-threed-escaper-landing-continuation-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7BFE", "C3:7E66", "ThreedEscaperLandingContinuation"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C4:8B2C` teleport landing-mode callback contract. This covers the event 670 Threed escaper landing sequence, the paired landing pulse tasks, and three randomized text-check loops that probe staged proximity before queueing the next text pointer.",
        "next": "Continue by pinning the adjacent `C0:A838` wrapper at `C3:7E68`, or take the newly callback-unlocked stage continuations from `notes/c3-source-pilot-frontier.md`.",
    },
    "threed-escaper-random-text-tail": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "threed_escaper_random_text_tail.asar.asm",
        "report": ROOT / "notes" / "c3-threed-escaper-random-text-tail-source-pilot.md",
        "manifest": ROOT / "build" / "c3-threed-escaper-random-text-tail-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7E66", "C3:7FCD", "ThreedEscaperRandomTextTail"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C0:A838` collision-state entry point. This covers the Threed escaper random-text tail after landing: random pause/pose setup, player-facing and party-look text waits, fixed-position route handoffs, and the release path before the next script cluster.",
        "next": "Continue with the adjacent `C3:7FCD..C3:835D` tail after reviewing its local script boundaries, or move to the remaining frontier gaps.",
    },
    "threed-escaper-late-route-tail": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "threed_escaper_late_route_tail.asar.asm",
        "report": ROOT / "notes" / "c3-threed-escaper-late-route-tail-source-pilot.md",
        "manifest": ROOT / "build" / "c3-threed-escaper-late-route-tail-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:7FCD", "C3:835D", "ThreedEscaperLateRouteTail"),
        ],
        "description": "High-ranked full-gap source-pilot tail for the remaining Threed escaper route cluster. This covers the bounce/release variants after the random-text tail, fixed-coordinate movement and party-member lookup paths, final text-yield halts, and live-area facing continuations before the animation-port flag switch helper.",
        "next": "Re-run the C3 frontier and continue with any remaining source-pilot gaps; this completes the formerly largest C3 Threed escaper gap.",
    },
    "flyover-scene-wait-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "flyover_scene_wait_paths.asar.asm",
        "report": ROOT / "notes" / "c3-flyover-scene-wait-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-flyover-scene-wait-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:ABE0", "C3:AFA3", "FlyoverSceneWaitPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the `$0028` low-byte wait helper plus the flyover/teleport-adjacent scene paths around ebsrc scripts 476-481, including flyover text scene dispatches, movement-to-coordinate handoffs, and direction tracking loops.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:AFA3..C3:B0B6` remains a compact terminal batch after the party-look helper.",
    },
    "party-look-meteorite-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_look_meteorite_paths.asar.asm",
        "report": ROOT / "notes" / "c3-party-look-meteorite-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-look-meteorite-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:AFA3", "C3:B06D", "PartyLookMeteoritePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the party-look-at-active-entity loop and ebsrc scripts 47-49, 53, and 55: party-member tracking/text handoffs, a dog-bye active-area text path, and a meteorite/Pokey snapshot-anchor text release before the next callback-heavy corridor.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:B06D..C3:B431` corridor should be split before the later `C4:6B51`/`C4:23DC` callback blockers.",
    },
    "party-member-orbit-damping-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_member_orbit_damping_paths.asar.asm",
        "report": ROOT / "notes" / "c3-party-member-orbit-damping-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-member-orbit-damping-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:B06D", "C3:B0B6", "PartyMemberOrbitDampingPaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the angle/vector callback contracts. This covers ebsrc script 51's compact party-member orbit loop: alternate-physics setup, z-offset positioning, projected angle/facing refresh, and damped vector cycling before the existing field-oscillation helper.",
        "next": "Continue with another callback-unlocked seam from `notes/c3-source-pilot-frontier.md`, especially the cast-screen and Threed escaper terminal batches.",
    },
    "position-watch-new-entity-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "position_watch_new_entity_paths.asar.asm",
        "report": ROOT / "notes" / "c3-position-watch-new-entity-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-position-watch-new-entity-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:D0A4", "C3:D1C9", "PositionWatchNewEntityPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 172-174 and the adjacent position/new-entity setup paths through the terminal batch before the `C0:A8B3` callback blocker.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:D1C9..C3:D913` bus-transition continuation is now promoted.",
    },
    "bus-transition-route-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bus_transition_route_paths.asar.asm",
        "report": ROOT / "notes" / "c3-bus-transition-route-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bus-transition-route-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:D1C9", "C3:D913", "BusTransitionRoutePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the post-position-watch bus and tunnel transition route cluster: follower/party-position loops, Tonzura bus movement/text paths, transition snapshot fanout calls, and repeated teleport-destination handoffs before the next `C3:D913` corridor.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:D913..C3:DB7A` remains a larger bus-transition continuation and should be split around local route/text boundaries.",
    },
    "twoson-bus-route-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "twoson_bus_route_paths.asar.asm",
        "report": ROOT / "notes" / "c3-twoson-bus-route-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-twoson-bus-route-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:B431", "C3:B70C", "TwosonBusRoutePaths"),
        ],
        "description": "High-ranked full-gap source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc scripts 64-72: the Twoson bus driver live-area/dialog loop, bus-to-Threed tunnel routes, return branches, transition snapshot handoffs, and short movement/text-yield paths before the tunnel ghost/zombie family at `C3:B70C`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:B70C..C3:BAA3` tunnel ghost/zombie family is already promoted.",
    },
    "bus-tunnel-desert-route-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "bus_tunnel_desert_route_paths.asar.asm",
        "report": ROOT / "notes" / "c3-bus-tunnel-desert-route-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-bus-tunnel-desert-route-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:D913", "C3:DB7A", "BusTunnelDesertRoutePaths"),
        ],
        "description": "High-ranked full-gap source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the bus tunnel/desert/bridge continuation around ebsrc scripts 211-220: route movement, transition snapshot handoffs, queued bus text, and recurring driver dialog loops before the shared bus-tunnel bridge helper at `C3:DB7A`.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the nearby `C3:DBF2..C3:DD4F` terminal batch is a compact follow-up, while the larger `C3:DBDB` helper corridor should remain split around local route boundaries.",
    },
    "townhall-direction-common-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "townhall_direction_common_paths.asar.asm",
        "report": ROOT / "notes" / "c3-townhall-direction-common-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-townhall-direction-common-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:8EF1", "C3:8FCE", "TownHallDirectionCommonPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the town hall direction common-tail continuation after ebsrc script 737, including the remaining direction setter entries and compact movement/text paths before the later coffee/tea visual-state blocker.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:8FCE..C3:9AC7` continuation is now promoted in `townhall-coffee-tea-gatekeeper-paths`.",
    },
    "townhall-coffee-tea-gatekeeper-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "townhall_coffee_tea_gatekeeper_paths.asar.asm",
        "report": ROOT / "notes" / "c3-townhall-coffee-tea-gatekeeper-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-townhall-coffee-tea-gatekeeper-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:8FCE", "C3:9AC7", "TownHallCoffeeTeaGatekeeperPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the remaining `C3:899E` town hall continuation through ebsrc scripts 744-757, the coffee/tea battle-overlay transition path, and the following gatekeeper/magic-cake movement and text paths before the shared `C3:9AC7` helper.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:9AC7..C3:9E01` corridor is now the next local town hall/magic-cake continuation.",
    },
    "flyover-intro-text-release-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "flyover_intro_text_release_paths.asar.asm",
        "report": ROOT / "notes" / "c3-flyover-intro-text-release-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-flyover-intro-text-release-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:9AC7", "C3:9AFA", "FlyoverIntroTextReleasePaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the compact battle-swirl footprint visual reset helper plus ebsrc script 765's fade-out, flyover wait, indexed flyover intro text scene, text yield, and release path.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:9AFA..C3:9E01` continuation should be split before the `C4:978E` callback blocker.",
    },
    "flyover-palette-random-movement-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "flyover_palette_random_movement_paths.asar.asm",
        "report": ROOT / "notes" / "c3-flyover-palette-random-movement-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-flyover-palette-random-movement-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:9AFA", "C3:9E01", "FlyoverPaletteRandomMovementPaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:978E` palette copy and `C0:AAB5` palette-fade wrapper contracts. This covers ebsrc scripts 766-772: flyover palette text/release paths, a random movement task, staged palette fade steps, bounce/visual countdown halt, party-look coordinate halt, area text movement halt, and a coordinate/text halt.",
        "next": "Continue with another callback-contract seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:9E01..9E8B` battle-swirl interaction family is already promoted.",
    },
    "battle-swirl-interaction-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "battle_swirl_interaction_paths.asar.asm",
        "report": ROOT / "notes" / "c3-battle-swirl-interaction-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-battle-swirl-interaction-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:9E01", "C3:9E8B", "BattleSwirlInteractionPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the battle-swirl/enemy-touch wait helper plus ebsrc scripts 773-778: down-direction release, compact coordinate halt, battle-swirl overlay handoff, delayed overlay task end, and pending-interaction set/clear releases.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:9E8B..C3:9FF2` continuation should be split before the later `C4:74A8` callback blocker.",
    },
    "battle-swirl-visual-countdown-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "battle_swirl_visual_countdown_paths.asar.asm",
        "report": ROOT / "notes" / "c3-battle-swirl-visual-countdown-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-battle-swirl-visual-countdown-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:9E8B", "C3:9EF2", "BattleSwirlVisualCountdownPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers ebsrc script 776's battle-swirl window-gfx/sound release path plus scripts 779-781, the compact left/down/down-from-registry visual countdown halts.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:9EF2..C3:9FF2` continuation should be split before the later `C4:74A8` callback blocker.",
    },
    "battle-swirl-recovery-party-spawns": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "battle_swirl_recovery_party_spawns.asar.asm",
        "report": ROOT / "notes" / "c3-battle-swirl-recovery-party-spawns-source-pilot.md",
        "manifest": ROOT / "build" / "c3-battle-swirl-recovery-party-spawns-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:9EF2", "C3:9FF2", "BattleSwirlRecoveryPartySpawns"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:74A8` fixed-color callback contract. This covers ebsrc scripts 782-784: the party lying-down spawn sequence, fixed-color recovery pulse helpers, lying-down bounce release, and the left/right wander loop.",
        "next": "Continue with another newly unlocked seam from `notes/c3-source-pilot-frontier.md`; the `C4:74A8` contract also unlocked several stage and Sky Runner/electric-effect ranges.",
    },
    "npc-attention-path-helpers": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "npc_attention_path_helpers.asar.asm",
        "report": ROOT / "notes" / "c3-npc-attention-path-helpers-source-pilot.md",
        "manifest": ROOT / "build" / "c3-npc-attention-path-helpers-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A401", "C3:A48A", "NpcAttentionPathHelpers"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the shared NPC attention-path helper cluster from ebsrc `C3A401.asm`: cached-neighbor setup, terrain/horizontal collision monitor tasks, attention coordinator gates, and the common release blink tail.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent script 19/20 continuations need the `C0:C48F` callback contract before promotion.",
    },
    "npc-attention-wide-distance-gate": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "npc_attention_wide_distance_gate.asar.asm",
        "report": ROOT / "notes" / "c3-npc-attention-wide-distance-gate-source-pilot.md",
        "manifest": ROOT / "build" / "c3-npc-attention-wide-distance-gate-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A48A", "C3:A4AC", "NpcAttentionWideDistanceGate"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C0:C48F` wide-distance gate contract. This covers the compact NPC-attention continuation after the shared path helpers: start the terrain-collision loop, bail through the common release tail if the cached-neighbor gate fails, and idle in the wide-distance test until the next walk-direction callback body.",
        "next": "Continue only after pinning the `C4:6B65` walk-direction callback at `C3:A4AC`, or choose another small callback-blocked frontier seam.",
    },
    "npc-attention-roundwalk-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "npc_attention_roundwalk_routes.asar.asm",
        "report": ROOT / "notes" / "c3-npc-attention-roundwalk-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-npc-attention-roundwalk-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A4AC", "C3:A606", "NpcAttentionRoundwalkRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by NPC attention callback contracts. This covers the script 19/20 continuation after the wide-distance gate: round-walk direction selection, player-context checks, bus-driver attention loops, collision-target chase setup, and movement-state handoffs before the next unpromoted collision-target branch.",
        "next": "Continue with the adjacent `C3:A606..C3:AA1E` attention-route tail after pinning or splitting the later `C0:A6D1` path, or move to another ready C3 seam.",
    },
    "npc-attention-collision-target-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "npc_attention_collision_target_routes.asar.asm",
        "report": ROOT / "notes" / "c3-npc-attention-collision-target-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-npc-attention-collision-target-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A606", "C3:A714", "NpcAttentionCollisionTargetRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch emitted after the round-walk continuation. This covers the collision-target random-step and player-fallback paths, horizontal bounce/chase loops, tight-distance wait/fallback loops, and the small bounce task before the next unpinned `C0:A6D1` route.",
        "next": "Continue with the adjacent `C3:A714..C3:AA1E` attention-route tail only after naming/pinning `C0:A6D1`, or move to the remaining `C0:A838` blocked early/7E66 gaps.",
    },
    "npc-attention-wide-distance-bounce-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "npc_attention_wide_distance_bounce_routes.asar.asm",
        "report": ROOT / "notes" / "c3-npc-attention-wide-distance-bounce-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-npc-attention-wide-distance-bounce-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A714", "C3:A780", "NpcAttentionWideDistanceBounceRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch emitted after the collision-target routes. This covers the wide-distance horizontal-bounce attention path: small bounce task startup, wait/fallback gates, player-direction revectoring, and return to the distance-gated loop before the next `C0:A6D1` callback branch.",
        "next": "Continue with `C3:A780..C3:AA1E` after pinning/naming `C0:A6D1`, or return to the `C0:A838` blocked early/7E66 C3 gaps.",
    },
    "npc-attention-arc-distance-routes": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "npc_attention_arc_distance_routes.asar.asm",
        "report": ROOT / "notes" / "c3-npc-attention-arc-distance-routes-source-pilot.md",
        "manifest": ROOT / "build" / "c3-npc-attention-arc-distance-routes-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A780", "C3:A922", "NpcAttentionArcDistanceRoutes"),
        ],
        "description": "High-ranked terminal source-pilot batch unlocked by the `C0:A6D1` collision-state entry point. This covers the NPC-attention arc/distance route tail: normalized attention tick setup, approach/fallback animation pulses, arc movement phase stepping, player-target revectoring, and tight-distance loop entry before the next `C0:A480` callback.",
        "next": "Continue with the remaining `C3:A922..C3:AA1E` route tail after naming/pinning `C0:A480`, or move to another ready frontier.",
    },
    "npc-attention-arc-distance-final-tail": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "npc_attention_arc_distance_final_tail.asar.asm",
        "report": ROOT / "notes" / "c3-npc-attention-arc-distance-final-tail-source-pilot.md",
        "manifest": ROOT / "build" / "c3-npc-attention-arc-distance-final-tail-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:A922", "C3:AA1E", "NpcAttentionArcDistanceFinalTail"),
        ],
        "description": "High-ranked source-pilot final tail unlocked by the `C0:A480` visual-profile refresh entry. This closes the NPC-attention arc/distance route corridor with the wide-distance gate fallback, player-target revectoring, visual-profile refresh, direction waits, and shared release handoff before the `AA1E` movement helper.",
        "next": "Re-run the C3 frontier and continue with any remaining source-pilot gaps; this closes the formerly `C0:A480`-blocked NPC-attention route tail.",
    },
    "party-member-hop-text-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "party_member_hop_text_paths.asar.asm",
        "report": ROOT / "notes" / "c3-party-member-hop-text-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-party-member-hop-text-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:B0B6", "C3:B13E", "PartyMemberHopTextPaths"),
        ],
        "description": "High-ranked source-pilot frontier seam emitted as labeled event/actionscript macro assembly. This covers the `C3B0B6` field2B32 vertical oscillation helper plus ebsrc script 50's party-member hop/text release with party-look task and z-hop task.",
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; adjacent `C3:B13E..C3:B431` should be split/pinned before the later `C4:23DC` and `C4:6B51` callback blockers.",
    },
    "meteorite-window-party-approach-paths": {
        "output": ROOT / "src" / "c3" / "event_scripts" / "meteorite_window_party_approach_paths.asar.asm",
        "report": ROOT / "notes" / "c3-meteorite-window-party-approach-paths-source-pilot.md",
        "manifest": ROOT / "build" / "c3-meteorite-window-party-approach-paths-source-pilot.json",
        "rows": [],
        "spans": [
            ("C3:B13E", "C3:B431", "MeteoriteWindowPartyApproachPaths"),
        ],
        "description": "High-ranked full-gap source-pilot seam unlocked by the `C4:23DC` centered color-window preset contract. This covers the rest of the meteorite/Pokey corridor after the party-member hop script: event 54's color-window presentation, event 52's temp-flag gated Pokey hop/text halt, event 53's meteorite text release, and the grouped party-approach movement/text paths up to the live-area wait helper at `C3:B431`.",
        "next": "Continue with another newly unlocked seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:B431..C3:B70C` Twoson bus route family is already promoted.",
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
        "next": "Continue with another high-ranked ready seam from `notes/c3-source-pilot-frontier.md`; the adjacent `C3:8EF1..C3:8FCE` town hall direction common continuation is now promoted.",
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


def catalog_constant(
    value: int,
    catalog: dict[int, dict[str, str]],
    *,
    prefix: str,
    formatter: Any,
    constants: dict[str, str],
) -> str | None:
    item = catalog.get(value)
    if item is None:
        return None
    name = sanitize_symbol(item["name"]).upper()
    suffix = name if name.startswith(f"{prefix}_") else f"{prefix}_{name}"
    symbol = f"!ACTIONSCRIPT_{suffix}"
    constants.setdefault(symbol, formatter(value))
    return symbol


def operand_expr(
    operand: Operand,
    *,
    instruction: Instruction,
    index: int,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
    direction_tempvar_writes: set[str],
) -> str:
    if operand.kind == "byte":
        value = int(operand.value)
        if instruction.opcode.name == "EVENT_SET_ANIMATION" and index == 0:
            symbol = catalog_constant(
                value,
                ACTIONSCRIPT_ANIMATION_IDS,
                prefix="ANIMATION",
                formatter=fmt_byte,
                constants=constants,
            )
            if symbol:
                return symbol
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
        if (
            operand.kind == "word"
            and instruction.opcode.name == "EVENT_WRITE_WORD_TEMPVAR"
            and index == 0
            and instruction.address.key in direction_tempvar_writes
        ):
            symbol = catalog_constant(
                value,
                ACTIONSCRIPT_DIRECTION_WORDS,
                prefix="DIRECTION",
                formatter=fmt_byte,
                constants=constants,
            )
            if symbol:
                return symbol
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


def callroutine_target(instruction: Instruction) -> Address | None:
    if instruction.opcode.name != "EVENT_CALLROUTINE":
        return None
    if not instruction.operands or not isinstance(instruction.operands[0].value, Address):
        return None
    return instruction.operands[0].value


def collect_direction_tempvar_writes(rows: list[RowSource]) -> set[str]:
    writes: set[str] = set()
    for row in rows:
        pending: list[str] = []
        for instruction in row.instructions:
            opcode_name = instruction.opcode.name
            if (
                opcode_name == "EVENT_WRITE_WORD_TEMPVAR"
                and instruction.operands
                and int(instruction.operands[0].value) in ACTIONSCRIPT_DIRECTION_WORDS
            ):
                pending.append(instruction.address.key)
                continue
            target = callroutine_target(instruction)
            if target and target.key in DIRECTION_TEMPVAR_CONSUMERS:
                writes.update(pending)
                pending = []
                continue
            if (
                opcode_name in TEMPVAR_REPLACING_OPCODES
                or opcode_name in TEMPVAR_MUTATING_OPCODES
                or target is not None
            ):
                pending = []
    return writes


def call_arg_expr(
    field: str,
    raw_args: list[int],
    cursor: int,
    *,
    constants: dict[str, str],
) -> tuple[str, int]:
    width = call_arg_width(field)
    if width is None or cursor + width > len(raw_args):
        raise ValueError(f"cannot render call argument field {field!r}")
    if width == 1:
        value = raw_args[cursor]
        if field == "direction_class_byte":
            symbol = catalog_constant(
                value,
                ACTIONSCRIPT_DIRECTION_WORDS,
                prefix="DIRECTION",
                formatter=fmt_byte,
                constants=constants,
            )
            if symbol:
                return symbol, cursor + 1
        return fmt_byte(raw_args[cursor]), cursor + 1
    if width == 2:
        value = raw_args[cursor] | (raw_args[cursor + 1] << 8)
        if field == "field2b32_word":
            symbol = catalog_constant(
                value,
                ACTIONSCRIPT_FIELD2B32_WORDS,
                prefix="FIELD2B32",
                formatter=fmt_word,
                constants=constants,
            )
            if symbol:
                return symbol, cursor + 2
        return fmt_word(value), cursor + 2
    value = raw_args[cursor] | (raw_args[cursor + 1] << 8) | (raw_args[cursor + 2] << 16)
    return fmt_long(value), cursor + 3


def macro_name(instruction: Instruction) -> str:
    if instruction.opcode.name == "EVENT_CALLROUTINE":
        target = callroutine_target(instruction)
        if target and target.key == "C0:9F82":
            count = next(
                int(operand.value)
                for operand in instruction.operands
                if operand.kind == "call_wordlist_count"
            )
            return f"EVENT_CHOOSE_RANDOM_SCRIPT_WORD_{count}"
        if target:
            fields = callroutine_schema(target, instruction.call_arg_count)
            if fields:
                return f"EVENT_CALLROUTINE_{callroutine_schema_suffix(fields)}"
        return f"EVENT_CALLROUTINE_{instruction.call_arg_count or 0}"
    if instruction.opcode.name in {"EVENT_SWITCH_JUMP_TEMPVAR", "EVENT_SWITCH_CALL_TEMPVAR"}:
        return f"{instruction.opcode.name}_{instruction.operands[0].value}"
    return instruction.opcode.name


def rendered_operands(
    instruction: Instruction,
    *,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
    direction_tempvar_writes: set[str],
) -> list[str]:
    target = callroutine_target(instruction)
    fields = callroutine_schema(target, instruction.call_arg_count) if target else None
    if target and fields:
        target_expr = operand_expr(
            instruction.operands[0],
            instruction=instruction,
            index=0,
            labels=labels,
            names=names,
            constants=constants,
            direction_tempvar_writes=direction_tempvar_writes,
        )
        raw_args = [int(operand.value) for operand in instruction.operands[1:]]
        cursor = 0
        rendered = [target_expr]
        for field in fields:
            value, cursor = call_arg_expr(field, raw_args, cursor, constants=constants)
            rendered.append(value)
        if cursor != len(raw_args):
            raise ValueError(f"unused call arguments for {target.key}")
        return rendered

    return [
        operand_expr(
            operand,
            instruction=instruction,
            index=index,
            labels=labels,
            names=names,
            constants=constants,
            direction_tempvar_writes=direction_tempvar_writes,
        )
        for index, operand in enumerate(instruction.operands)
    ]


def render_instruction(
    instruction: Instruction,
    *,
    labels: dict[str, str],
    names: dict[str, list[str]],
    constants: dict[str, str],
    direction_tempvar_writes: set[str],
) -> str:
    args = ", ".join(
        rendered_operands(
            instruction,
            labels=labels,
            names=names,
            constants=constants,
            direction_tempvar_writes=direction_tempvar_writes,
        )
    )
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
        "EVENT_CALLROUTINE_5": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>, <arg2>, <arg3>, <arg4>"],
        "EVENT_CALLROUTINE_6": ["    db $42", "    dl <target>", "    db <arg0>, <arg1>, <arg2>, <arg3>, <arg4>, <arg5>"],
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
        "EVENT_CALLROUTINE_5": "target, arg0, arg1, arg2, arg3, arg4",
        "EVENT_CALLROUTINE_6": "target, arg0, arg1, arg2, arg3, arg4, arg5",
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
    for name in sorted(used_macros):
        fields = CALLROUTINE_SCHEMA_MACROS.get(name)
        if not fields:
            continue
        body = ["    db $42", "    dl <target>"]
        for field in fields:
            width = call_arg_width(field)
            if width == 1:
                body.append(f"    db <{field}>")
            elif width == 2:
                body.append(f"    dw <{field}>")
            elif width == 3:
                body.append(f"    dl <{field}>")
            else:
                raise ValueError(f"cannot emit schema macro for field {field!r}")
        bodies[name] = body
        args[name] = ", ".join(["target", *fields])
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
    direction_tempvar_writes = collect_direction_tempvar_writes(rows)

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
                render_instruction(
                    instruction,
                    labels=labels,
                    names=names,
                    constants=constants,
                    direction_tempvar_writes=direction_tempvar_writes,
                )
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
    constants: dict[str, str],
    used_macros: set[str],
    direction_tempvar_write_count: int,
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
    readability_lines = []
    if any(symbol.startswith("!ACTIONSCRIPT_ANIMATION_") for symbol in constants):
        readability_lines.append(
            "- Known `EVENT_SET_ANIMATION` selectors render as `!ACTIONSCRIPT_ANIMATION_*` constants."
        )
    if any(symbol.startswith("!ACTIONSCRIPT_FIELD2B32_") for symbol in constants):
        readability_lines.append(
            "- `C0:A685` calls render through `%EVENT_CALLROUTINE_FIELD2B32(..., field2b32_word)`, preserving the same little-endian bytes with a word-shaped operand."
        )
    if any(symbol.startswith("!ACTIONSCRIPT_DIRECTION_") for symbol in constants):
        readability_lines.append(
            "- Known direction-class callback bytes render as `!ACTIONSCRIPT_DIRECTION_*` constants."
        )
    if direction_tempvar_write_count:
        readability_lines.append(
            "- Direction tempvar writes render as `!ACTIONSCRIPT_DIRECTION_*` constants only when a later direction/vector callback consumes them in the same emitted row, with no intervening tempvar rewrite or unrelated native callback."
        )
    schema_macros = sorted(macro for macro in used_macros if macro in CALLROUTINE_SCHEMA_MACROS)
    if schema_macros:
        visible = ", ".join(f"`%{macro}`" for macro in schema_macros[:4])
        suffix = f", +{len(schema_macros) - 4}" if len(schema_macros) > 4 else ""
        readability_lines.append(
            f"- Known native callback argument schemas render as field-shaped macros: {visible}{suffix}."
        )
    if readability_lines:
        lines.extend(["", "## Source Readability", "", *readability_lines])
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
    used_macros = {macro_name(instruction) for row in rows for instruction in row.instructions}
    direction_tempvar_writes = collect_direction_tempvar_writes(rows)

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
            constants=constants,
            used_macros=used_macros,
            direction_tempvar_write_count=len(direction_tempvar_writes),
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
