from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import IntEnum
import tomllib
import json
import os
import re

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
    MaxWorkoutsToDownload: int = 5
    ExcludeWorkoutTypes: List[str] = []
    BackupFolder: str = "p2g_output"
    Api: PelotonApiSettings = PelotonApiSettings()

class GarminApiSettings(BaseModel):
    SsoSignInUrl: str = "https://sso.garmin.com/sso/signin"
    UploadActivityUrl: str = "https://connectapi.garmin.com/upload-service/upload"

class GarminSettings(BaseModel):
    Email: Optional[str] = None
    Password: Optional[str] = None
    TwoStepVerificationEnabled: bool = False
    Upload: bool = True
    FormatToUpload: FileFormatEnum = FileFormatEnum.Fit
    Api: GarminApiSettings = GarminApiSettings()
    OAuth1Token: Optional[str] = None
    OAuth1TokenSecret: Optional[str] = None

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

def load_settings(config_path: str = "config.toml") -> Settings:
    if os.path.exists(config_path):
        with open(config_path, 'rb') as f:
            if config_path.endswith('.toml'):
                data = tomllib.load(f)
            else:
                data = json.load(f)
            return Settings.model_validate(data)
    else:
        # Fallback to env vars if file doesn't exist
        # This will error if required fields are missing
        return Settings()

def save_garmin_tokens(config_path: str, token: str, secret: str):
    """
     updates the garmin oauth1 tokens in the config file.
     supports both json and toml (via manual text patching for toml since we lack a writer).
    """
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}, cannot save tokens.")
        return

    if config_path.endswith('.json'):
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        if "Garmin" not in data:
            data["Garmin"] = {}
        
        data["Garmin"]["OAuth1Token"] = token
        data["Garmin"]["OAuth1TokenSecret"] = secret
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=4)
            
    else:
        # TOML - Manual patching
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        in_garmin = False
        token_written = False
        secret_written = False
        
        garmin_header_pattern = re.compile(r'^\s*\[Garmin\]\s*')
        section_header_pattern = re.compile(r'^\s*\[.*\]\s*')
        key_pattern = re.compile(r'^\s*(\w+)\s*=')

        for line in lines:
            if garmin_header_pattern.match(line):
                in_garmin = True
                new_lines.append(line)
                continue
            
            if in_garmin and section_header_pattern.match(line):
                # Leaving Garmin section, write tokens if we haven't yet
                if not token_written:
                    new_lines.append(f'OAuth1Token = "{token}"\n')
                    token_written = True
                if not secret_written:
                    new_lines.append(f'OAuth1TokenSecret = "{secret}"\n')
                    secret_written = True
                in_garmin = False
            
            if in_garmin:
                # Check if we are updating existing keys
                match = key_pattern.match(line)
                if match:
                    key = match.group(1)
                    if key == "OAuth1Token":
                        new_lines.append(f'OAuth1Token = "{token}"\n')
                        token_written = True
                        continue
                    elif key == "OAuth1TokenSecret":
                        new_lines.append(f'OAuth1TokenSecret = "{secret}"\n')
                        secret_written = True
                        continue
            
            new_lines.append(line)
        
        # If we reached the end of file and were still in Garmin section (or never left it properly because it was the last one)
        # or if we never found the section but might want to append? (Simpler to assume [Garmin] exists as per app logic)
        if in_garmin:
             if not token_written:
                new_lines.append(f'OAuth1Token = "{token}"\n')
            
             if not secret_written:
                new_lines.append(f'OAuth1TokenSecret = "{secret}"\n')

        with open(config_path, 'w') as f:
            f.writelines(new_lines)

