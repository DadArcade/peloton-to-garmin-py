from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import IntEnum
import json
import os

class FileFormatEnum(IntEnum):
    Fit = 0
    Tcx = 1
    Json = 2

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
        return super()._missing_(value)

class PreferredLapTypeEnum(IntEnum):
    Default = 0
    Distance = 1
    Class_Segments = 2
    Class_Targets = 3

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.name.lower() == value.lower():
                    return member
        return super()._missing_(value)

class AppSettings(BaseModel):
    EnablePolling: bool = False
    PollingIntervalSeconds: int = 86400
    CheckForUpdates: bool = True
    CloseConsoleOnFinish: bool = False

class CyclingSettings(BaseModel):
    PreferredLapType: PreferredLapTypeEnum = PreferredLapTypeEnum.Default

class RunningSettings(BaseModel):
    PreferredLapType: PreferredLapTypeEnum = PreferredLapTypeEnum.Default

class RowingSettings(BaseModel):
    PreferredLapType: PreferredLapTypeEnum = PreferredLapTypeEnum.Default

class StrengthSettings(BaseModel):
    DefaultSecondsPerRep: int = 3

class FormatSettings(BaseModel):
    Fit: bool = True
    Json: bool = False
    Tcx: bool = False
    SaveLocalCopy: bool = True
    IncludeTimeInHRZones: bool = True
    IncludeTimeInPowerZones: bool = True
    Cycling: CyclingSettings = CyclingSettings()
    Running: RunningSettings = RunningSettings()
    Rowing: RowingSettings = RowingSettings()
    Strength: StrengthSettings = StrengthSettings()

class PelotonApiSettings(BaseModel):
    ApiUrl: str = "https://api.onepeloton.com/"
    AuthDomain: str = "auth.onepeloton.com"
    AuthClientId: str = "WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM"

class PelotonSettings(BaseModel):
    Email: str
    Password: str
    NumWorkoutsToDownload: int = 5
    ExcludeWorkoutTypes: List[str] = []
    Api: PelotonApiSettings = PelotonApiSettings()

class GarminApiSettings(BaseModel):
    SsoSignInUrl: str = "https://sso.garmin.com/sso/signin"
    UploadActivityUrl: str = "https://connectapi.garmin.com/upload-service/upload"

class GarminSettings(BaseModel):
    Email: str
    Password: str
    TwoStepVerificationEnabled: bool = False
    Upload: bool = True
    FormatToUpload: FileFormatEnum = FileFormatEnum.Fit
    Api: GarminApiSettings = GarminApiSettings()

class Settings(BaseSettings):
    App: AppSettings = AppSettings()
    Format: FormatSettings = FormatSettings()
    Peloton: PelotonSettings
    Garmin: GarminSettings

    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        env_prefix='P2G_',
        extra='ignore'
    )

def load_settings(config_path: str = "configuration.local.json") -> Settings:
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
            return Settings.model_validate(data)
    else:
        # Fallback to env vars if file doesn't exist
        # This will error if required fields are missing
        return Settings()
