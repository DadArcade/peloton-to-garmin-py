from fit_tool.profile.profile_type import (
    ExerciseCategory, ShoulderPressExerciseName, WarmUpExerciseName,
    PlankExerciseName, RowExerciseName, CurlExerciseName, CrunchExerciseName,
    SquatExerciseName, FlyeExerciseName, HipRaiseExerciseName, OlympicLiftExerciseName,
    CoreExerciseName, BenchPressExerciseName, HipStabilityExerciseName,
    PushUpExerciseName, DeadliftExerciseName, HipSwingExerciseName,
    LateralRaiseExerciseName, LungeExerciseName, ShrugExerciseName,
    CarryExerciseName, TricepsExtensionExerciseName, SitUpExerciseName,
    ChopExerciseName, SetType
)

class GarminExercise:
    def __init__(self, category: int, name: int):
        self.category = category
        self.name = name

# Peloton Exercise IDs to Garlic Mappings
IGNORED_PELOTON_EXERCISES = {
    "b067c9f7a1e4412190b0f8eb3c6128e3", # Active Recovery
    "98cde50f696746ff98727d5362229cfb", # AMRAP
    "e54412161b594e54a86d6ef23ea3d017", # Demo
    "a76c5edc0641475189442ecad456057a", # Transition
    "0b67e950426440fe8b4eadc426320a56", # Warmup
}

STRENGTH_EXERCISE_MAPPINGS = {
    # A
    "01251235527748368069f9dc898aadf3": GarminExercise(ExerciseCategory.SHOULDER_PRESS, ShoulderPressExerciseName.ARNOLD_PRESS),
    "1b3400e0aade45e58d2f42cf19af0f40": GarminExercise(ExerciseCategory.WARM_UP, WarmUpExerciseName.ARM_CIRCLES),
    # B
    "46112d47abe24b53ad1fa8e75edcf545": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.BEAR_CRAWL),
    "d60a1dd8824a49a4926f826b24f3b061": GarminExercise(ExerciseCategory.ROW, RowExerciseName.ONE_ARM_BENT_OVER_ROW),
    "43d404595338443baab306a6589ae7fc": GarminExercise(ExerciseCategory.CURL, CurlExerciseName.STANDING_DUMBBELL_BICEPS_CURL),
    "550b2c852a9547b18ca8e6240c5c6750": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.BICYCLE_CRUNCH),
    "df8e18c5082f408b8490c4adcb0678b5": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.PLANK_WITH_KNEE_TO_ELBOW),
    "adbac11d3b714403ba22a175a8c95837": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.HOLLOW_ROCK),
    "46d30aa1a4a245ada8a5e5ff8f3e7662": GarminExercise(ExerciseCategory.SQUAT, SquatExerciseName.SQUAT),
    # C
    "45207949aa384783b5d71451f7fe1c3d": GarminExercise(ExerciseCategory.FLYE, FlyeExerciseName.DUMBBELL_FLYE),
    "5749daaf9be3448397af9d813d760ff3": GarminExercise(ExerciseCategory.HIP_RAISE, HipRaiseExerciseName.CLAMS),
    "f2a28d3ebf3c4844a704d2b94e283099": GarminExercise(ExerciseCategory.OLYMPIC_LIFT, OlympicLiftExerciseName.DUMBBELL_CLEAN),
    "3695ef0ec2ce484faedc8ce2bfa2819d": GarminExercise(ExerciseCategory.CURL, CurlExerciseName.SEATED_DUMBBELL_BICEPS_CURL),
    "b62c0d2189ae4c2fb6f5203fa145010a": GarminExercise(ExerciseCategory.CORE, CoreExerciseName.CRISS_CROSS),
    "61ac0d64602c48fba25af7e5e5dc1f97": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.CRUNCH),
    "4899db2664ce47da8ec14282282d3b0d": GarminExercise(ExerciseCategory.BENCH_PRESS, BenchPressExerciseName.CLOSE_GRIP_BARBELL_BENCH_PRESS),
    "a66b797fc2014b799cc0cb114d9c5079": GarminExercise(ExerciseCategory.CURL, CurlExerciseName.CROSS_BODY_DUMBBELL_HAMMER_CURL),
    # D
    "3001f790c7ca471e8ba6d1b57a3a842d": GarminExercise(ExerciseCategory.HIP_STABILITY, HipStabilityExerciseName.DEAD_BUG),
    "cd6046306b2c4c4a8f40e169ec924eb9": GarminExercise(ExerciseCategory.DEADLIFT, DeadliftExerciseName.DUMBBELL_DEADLIFT),
    "ce8c746fb5224e9dbc401fef0013a54f": GarminExercise(ExerciseCategory.PUSH_UP, PushUpExerciseName.PUSH_UP),
    "6dd608bcc9394b49a68a918359839202": GarminExercise(ExerciseCategory.DEADLIFT, DeadliftExerciseName.SINGLE_LEG_ROMANIAN_DEADLIFT_WITH_DUMBBELL),
    "7d82b59462a54e61926077ded0becae5": GarminExercise(ExerciseCategory.SQUAT, SquatExerciseName.DUMBBELL_SQUAT),
    "cd25b61809884d60adb1d97cd646f4fd": GarminExercise(ExerciseCategory.DEADLIFT, DeadliftExerciseName.SUMO_DEADLIFT),
    "4460e019d86c4e4ebe7284bb16d128d2": GarminExercise(ExerciseCategory.HIP_SWING, HipSwingExerciseName.SINGLE_ARM_DUMBBELL_SWING),
    "5ab0baeebee94d3995cb7f2b0332f430": GarminExercise(ExerciseCategory.SQUAT, SquatExerciseName.THRUSTERS),
    "843d434f59f941c0826fc0fe15eb0236": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.PLANK_PIKES),
    # F
    "6091566fa0674afd96a22fcec3ab18ce": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.FLUTTER_KICKS),
    "1c0403c4d7264d83b1c75d18c8cdac4f": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.SIDE_PLANK),
    "223e8e6918d64d9097064d34e3b17e77": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.SIDE_PLANK_WITH_REACH_UNDER),
    "feb44f24e2b8487b870a35f4501069be": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.PLANK),
    "78b0a09ce8274e9c8beac6aadd50454b": GarminExercise(ExerciseCategory.TRICEPS_EXTENSION, TricepsExtensionExerciseName.DUMBBELL_LYING_TRICEPS_EXTENSION),
    "ed18d837c14746c5af38d4fa03b56918": GarminExercise(ExerciseCategory.LUNGE, LungeExerciseName.DUMBBELL_LUNGE),
    "8ef53816dc414bed800e8bf0cee3c484": GarminExercise(ExerciseCategory.LUNGE, LungeExerciseName.DUMBBELL_LUNGE),
    "a9cefac3b8234bc0bc0ee8deb62d67d3": GarminExercise(ExerciseCategory.LATERAL_RAISE, LateralRaiseExerciseName.FRONT_RAISE),
    "e099e49b59564ef4a7198bf87cdc1446": GarminExercise(ExerciseCategory.LATERAL_RAISE, LateralRaiseExerciseName.FRONT_RAISE),
    # G
    "588e35f7067842979485ff1e4f80df26": GarminExercise(ExerciseCategory.SQUAT, SquatExerciseName.GOBLET_SQUAT),
    # H
    "114ce849b47a4fabbaad961188bf4f7d": GarminExercise(ExerciseCategory.CURL, CurlExerciseName.DUMBBELL_HAMMER_CURL),
    "194cc4f6a88c4abd80afe9bbddb25915": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.STRAIGHT_ARM_PLANK),
    "d06c8e68481741de849e4101eda76855": GarminExercise(ExerciseCategory.SHRUG, ShrugExerciseName.DUMBBELL_UPRIGHT_ROW),
    "a6833a0f9c35489585398d1f293600de": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.SIDE_PLANK),
    "06a504988ace45faabd927af1479f454": GarminExercise(ExerciseCategory.HIP_RAISE, HipRaiseExerciseName.BARBELL_HIP_THRUST_ON_FLOOR),
    "060174b84e3744e6a19fe4ce80411113": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.HOLLOW_ROCK),
    "b264d06330c5442d83ffeaff878cf31d": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.HOLLOW_ROCK),
    # L
    "fb63e1ea19264145ae6856eefacbcb22": GarminExercise(ExerciseCategory.LUNGE, LungeExerciseName.SLIDING_LATERAL_LUNGE),
    "c80ac3adb6f74487808f361876ba326c": GarminExercise(ExerciseCategory.ROW, RowExerciseName.ONE_ARM_BENT_OVER_ROW),
    "2635cbe093a140e0be83be83fa594d8b": GarminExercise(ExerciseCategory.LATERAL_RAISE, LateralRaiseExerciseName.SEATED_LATERAL_RAISE),
    "7a5f7d80783f4b77b44dad8d6a0d2fae": GarminExercise(ExerciseCategory.HIP_RAISE, HipRaiseExerciseName.LEG_LIFT),
    # N
    "3caccc04fea1402cab9887ce589833ea": GarminExercise(ExerciseCategory.SHOULDER_PRESS, ShoulderPressExerciseName.OVERHEAD_DUMBBELL_PRESS),
    "802f10996b5048d08f320d8661f13ee1": GarminExercise(ExerciseCategory.BENCH_PRESS, BenchPressExerciseName.NEUTRAL_GRIP_DUMBBELL_BENCH_PRESS),
    # O
    "d5ec25fe793f4318a6891607bd3c9259": GarminExercise(ExerciseCategory.CRUNCH, CoreExerciseName.SIDE_BEND),
    "00046ee377554425866b0a1963b98589": GarminExercise(ExerciseCategory.LATERAL_RAISE, LateralRaiseExerciseName.SEATED_LATERAL_RAISE),
    "12057d5f9e144913a824bcae5706966c": GarminExercise(ExerciseCategory.CARRY, CarryExerciseName.OVERHEAD_CARRY),
    "f260623343e74d37b165071ee5903199": GarminExercise(ExerciseCategory.TRICEPS_EXTENSION, TricepsExtensionExerciseName.OVERHEAD_DUMBBELL_TRICEPS_EXTENSION),
    "ef0279948228409298cd6bf62c5b122c": GarminExercise(ExerciseCategory.SHOULDER_PRESS, ShoulderPressExerciseName.OVERHEAD_DUMBBELL_PRESS),
    # P
    "8af39d3485224ac19f7d8659d30524e7": GarminExercise(ExerciseCategory.PUSH_UP, PushUpExerciseName.SHOULDER_PUSH_UP),
    "1c4d81ad487849a6995f93e1a6a4b1e4": GarminExercise(ExerciseCategory.PUSH_UP, PushUpExerciseName.PUSH_UP),
    "ad8e4f16bf5a450db7d3b72b8ff7b014": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.STRAIGHT_ARM_PLANK_WITH_SHOULDER_TOUCH),
    "67c956e4da6542d1bbfa0625d569f018": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.PLANK_PIKES),
    "ae8ada57d3f0424ba391effec04e1e5f": GarminExercise(ExerciseCategory.SHOULDER_PRESS, ShoulderPressExerciseName.DUMBBELL_PUSH_PRESS),
    # R
    "c430accc3802486a86ad2de9cb8f01cc": GarminExercise(ExerciseCategory.LUNGE, LungeExerciseName.REVERSE_SLIDING_LUNGE),
    "3df6a1136a7a4e4db31e104c7d5a0fcf": GarminExercise(ExerciseCategory.FLYE, FlyeExerciseName.INCLINE_DUMBBELL_FLYE),
    "ed9adea36e77459dab7c189884ceb7ab": GarminExercise(ExerciseCategory.ROW, RowExerciseName.RENEGADE_ROW),
    "0b853e45afb04c31968b20fc7deaa718": GarminExercise(ExerciseCategory.CORE, CoreExerciseName.ROLL_UP),
    "165ed4b439204800b9d88d85363f0609": GarminExercise(ExerciseCategory.ROW, RowExerciseName.DUMBBELL_ROW),
    "a17b8d35d1264a2fbabe3ab28df458dc": GarminExercise(ExerciseCategory.DEADLIFT, DeadliftExerciseName.DUMBBELL_DEADLIFT),
    "5c7b2bc65abc4c44849e2119f1338120": GarminExercise(ExerciseCategory.CORE, CoreExerciseName.RUSSIAN_TWIST),
    # S
    "f6a10df381004afba2a2b63447d9968f": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.LEG_LEVERS),
    "0f9b2d6f18b247bd950d60bbbefd19f3": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.LEG_LEVERS),
    "5b33283433e7479390c0d5fc11722f80": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.STRAIGHT_ARM_PLANK_WITH_SHOULDER_TOUCH),
    "97f0a46ff7ad4f03ac9b2cfac96e3b40": GarminExercise(ExerciseCategory.SHOULDER_PRESS, ShoulderPressExerciseName.OVERHEAD_DUMBBELL_PRESS),
    "a466cebb07794281a367dd686794aa62": GarminExercise(ExerciseCategory.CURL, CurlExerciseName.STANDING_DUMBBELL_BICEPS_CURL),
    "32c3f3f1f90446ad8e58589b45ae891b": GarminExercise(ExerciseCategory.CORE, CoreExerciseName.SINGLE_LEG_STRETCH),
    "3c72e60de73d43f4b5a774c90dea90cd": GarminExercise(ExerciseCategory.TRICEPS_EXTENSION, TricepsExtensionExerciseName.DUMBBELL_LYING_TRICEPS_EXTENSION),
    "0ddf8f94acfe4c2289aef5a9bf59e8d9": GarminExercise(ExerciseCategory.OLYMPIC_LIFT, OlympicLiftExerciseName.SINGLE_ARM_DUMBBELL_SNATCH),
    "28833fd99466476ea273d6b94747e3db": GarminExercise(ExerciseCategory.SQUAT, SquatExerciseName.DUMBBELL_SPLIT_SQUAT),
    "021047bf0cff470bb2d11f94d3539cfe": GarminExercise(ExerciseCategory.FLYE, FlyeExerciseName.DUMBBELL_FLYE),
    "b617914877c24dac85df81621872e056": GarminExercise(ExerciseCategory.CORE, CoreExerciseName.BICYCLE),
    "34dd5f694fd44d15bb0eead604dfebae": GarminExercise(ExerciseCategory.ROW, RowExerciseName.REVERSE_GRIP_BARBELL_ROW),
    # T
    "5bb2d37f052e4d2faf1b0f1de4489531": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.KNEELING_SIDE_PLANK_WITH_LEG_LIFT),
    "6be91da1de1c49f4b34bf358bdbf3bbc": GarminExercise(ExerciseCategory.CRUNCH, CrunchExerciseName.STANDING_SIDE_CRUNCH),
    "0a983b7dfca7400a92761380ff9d351a": GarminExercise(ExerciseCategory.TRICEPS_EXTENSION, TricepsExtensionExerciseName.BODY_WEIGHT_DIP),
    "da89d743904640d58e8b3f667f08783c": GarminExercise(ExerciseCategory.TRICEPS_EXTENSION, TricepsExtensionExerciseName.DUMBBELL_KICKBACK),
    "3069e7ba28b84005b71c16a3781dda8d": GarminExercise(ExerciseCategory.SIT_UP, SitUpExerciseName.BENT_KNEE_V_UP),
    "d463a4dc0cf640e0a58f3aa058c5b1a0": GarminExercise(ExerciseCategory.PUSH_UP, PushUpExerciseName.PUSH_UP),
    "cc70d143627c45e5b64e2cb116619899": GarminExercise(ExerciseCategory.PLANK, PlankExerciseName.CROSS_BODY_MOUNTAIN_CLIMBER),
    # V
    "715caba11593427299342c378b444e05": GarminExercise(ExerciseCategory.SIT_UP, SitUpExerciseName.V_UP),
    # W
    "05d60a7d022f41dd8d3a8da07bca6041": GarminExercise(ExerciseCategory.CHOP, ChopExerciseName.DUMBBELL_CHOP),
    "94e3c37e0cb245f78e195b115a400112": GarminExercise(ExerciseCategory.BENCH_PRESS, BenchPressExerciseName.WIDE_GRIP_BARBELL_BENCH_PRESS),
    "d861cb497fcc4e1cba994b7a949a3bac": GarminExercise(ExerciseCategory.ROW, RowExerciseName.WIDE_GRIP_SEATED_CABLE_ROW),
    "258884d9586b45b3973228147a6b0c48": GarminExercise(ExerciseCategory.SHOULDER_PRESS, ShoulderPressExerciseName.OVERHEAD_DUMBBELL_PRESS),
    "f05ccd12e95c49aa93ac66bff7ec8df0": GarminExercise(ExerciseCategory.ROW, RowExerciseName.WIDE_GRIP_SEATED_CABLE_ROW),
    "d5dfeae09db149fca2c5781d0478e87b": GarminExercise(ExerciseCategory.CURL, CurlExerciseName.DUMBBELL_WRIST_CURL),
    "52dfd0316bd94aae9e461d8d3a69dff1": GarminExercise(ExerciseCategory.LATERAL_RAISE, LateralRaiseExerciseName.SEATED_LATERAL_RAISE),
    # Z
    "96b11092c5064b779b371462e2509e82": GarminExercise(ExerciseCategory.CURL, CurlExerciseName.STANDING_ALTERNATING_DUMBBELL_CURLS),
}

def is_rest(peloton_exercise_id: str) -> bool:
    return peloton_exercise_id == "3ca251f6d68746ad91aebea5c89694ca"
