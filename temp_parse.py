import re

data = '''Absorb20 > 40NoneNoneNoneNone
AeroblastNoneNone95% > 100%NoneNone
Air CutterNoneNone95% > 100%NoneNone
Air SlashNoneNone95% > 100%NoneNone
Aqua TailNoneNone90% > 95%NoneNone
Astonish30 > 40NoneNoneNoneNone
Baby-Doll EyesNone30 > 10NoneNoneNone
BarrageNoneNone85% > 100%NoneNone
BelchNoneNone90% > 100%NoneNone
BindNoneNone85% > 100%NoneNone
Blaze KickNoneNone90% > 100%NoneNone
BlizzardNoneNone70% > 80%NoneNone
Blue FlareNoneNone85% > 90%NoneNone
Bolt StrikeNoneNone85% > 90%NoneNone
Bone ClubNoneNone85% > 100%NoneNone
BonemerangNoneNone90% > 100%NoneNone
BounceNoneNone85% > 95%NoneNone
CaptivateNone20 > 5NoneNoneNone
Charge Beam50 > 40None90% > 100%70% > 100%None
CharmNone20 > 5NoneNoneNone
Circle ThrowNoneNone90% > 95%NoneNone
ClampNoneNone85% > 100%NoneNone
Comet PunchNoneNone85% > 90%NoneNone
ConfideNone20 > 10NoneNoneNone
CovetNoneNoneNoneNoneNormal > Fairy
CrabhammerNoneNone90% > 100%NoneNone
Cross ChopNoneNone80% > 90%NoneNone
CutNoneNone95% > 100%NoneNone
Dark VoidNoneNone50% > 80%NoneNone
Diamond StormNoneNone95% > 100%NoneNone
Double HitNoneNone90% > 100%NoneNone
Double SlapNoneNone85% > 100%NoneNone
Draco MeteorNoneNone90% > 100%NoneNone
Dragon RushNoneNone75% > 85%NoneNone
Dragon TailNoneNone90% > 95%NoneNone
Drill RunNoneNone95% > 100%NoneNone
Dual ChopNoneNone90% > 100%NoneNone
Dual WingbeatNoneNone90% > 100%NoneNone
Eerie ImpulseNone15 > 5NoneNoneNone
ElectrowebNoneNone95% > 100%NoneNone
Fake OutNone10 > 5NoneNoneNone
Fake TearsNone20 > 5NoneNoneNone
Feather DanceNone15 > 5NoneNoneNone
Fire FangNoneNone95% > 100%NoneNone
Fire SpinNoneNone85% > 100%NoneNone
FlashNoneNone100% > 70%NoneNone
Fleur CannonNoneNone90% > 100%NoneNone
FlyNoneNone95% > 100%NoneNone
Flying PressNoneNone95% > 100%NoneNone
Focus BlastNoneNone70% > 80%NoneNone
Freeze ShockNoneNone90% > 100%NoneNone
Frenzy PlantNoneNone90% > 100%NoneNone
Frost BreathNoneNone90% > 100%NoneNone
Frustration?? > 102NoneNoneNoneNone
Fury AttackNoneNone85% > 100%NoneNone
Fury SwipesNoneNone80% > 90%NoneNone
Gear GrindNoneNone85% > 100%NoneNone
Giga ImpactNoneNone90% > 100%NoneNone
GlaciateNoneNone95% > 100%NoneNone
Grass WhistleNoneNone55% > 70%NoneNone
GrowlNone40 > 10NoneNoneNone
Gunk ShotNoneNone80% > 85%NoneNone
Hammer ArmNoneNone90% > 100%NoneNone
HardenNone40 > 5NoneNoneNone
Head SmashNoneNone80% > 85%NoneNone
Heat WaveNoneNone90% > 100%NoneNone
High HorsepowerNoneNone95% > 100%NoneNone
HurricaneNoneNone70% > 80%NoneNone
Hydro CannonNoneNone90% > 100%NoneNone
Hydro PumpNoneNone80% > 85%NoneNone
Hyper BeamNoneNone90% > 100%NoneNone
Hyper FangNoneNone90% > 100%NoneNone
HypnosisNoneNone60% > 70%NoneNone
Ice BurnNoneNone90% > 100%NoneNone
Ice FangNoneNone95% > 100%NoneNone
Ice HammerNoneNone90% > 100%NoneNone
Icicle CrashNoneNone90% > 100%NoneNone
Icy WindNoneNone95% > 100%NoneNone
Iron TailNoneNone75% > 85%NoneNone
KinesisNoneNone80% > 100%NoneNone
Leaf StormNoneNone90% > 100%NoneNone
Leaf TornadoNoneNone90% > 100%50% > 30%None
Leech SeedNoneNone90% > 100%NoneNone
LeerNone30 > 10NoneNoneNone
Lick30 > 40NoneNoneNoneNone
Light of RuinNoneNone90% > 100%NoneNone
Lovely KissNoneNone75% > 80%NoneNone
Magma StormNoneNone75% > 90%NoneNone
Mega Drain40 > 60NoneNoneNoneNone
Mega KickNoneNone75% > 85%NoneNone
Mega PunchNoneNone85% > 100%NoneNone
MegahornNoneNone85% > 90%NoneNone
Metal ClawNoneNone95% > 100%NoneNone
Metal SoundNone40 > 585% > 100%NoneNone
Meteor BeamNoneNone90% > 100%NoneNone
Meteor MashNoneNone90% > 100%NoneNone
Mirror ShotNoneNone85% > 100%30% > 20%None
Misty Explosion100 > 200NoneNoneNoneNone
Mud BombNoneNone85% > 100%30% > 20%None
Muddy WaterNoneNone85% > 95%NoneNone
Nature's MadnessNoneNone90% > 100%NoneNone
Night DazeNoneNone95% > 100%40% > 30%None
Noble RoarNone30 > 10NoneNoneNone
Octazooka65 > 80None85% > 100%50% > 30%None
Origin PulseNoneNone85% > 100%NoneNone
OverheatNoneNone90% > 100%NoneNone
Pin MissileNoneNone95% > 100%NoneNone
Play NiceNone20 > 10NoneNoneNone
Play RoughNoneNone90% > 100%NoneNone
Poison PowderNoneNone75% > 90%NoneNone
Power WhipNoneNone85% > 90%NoneNone
Precicipe BladesNoneNone85% > 100%NoneNone
Psycho BoostNoneNone90% > 100%NoneNone
Razor LeafNoneNone95% > 100%NoneNone
Razor ShellNoneNone95% > 100%NoneNone
Return?? > 102NoneNoneNoneNone
Roar of TimeNoneNone90% > 100%NoneNone
Rock BlastNoneNone90% > 100%NoneNone
Rock ClimbNoneNone85% > 95%NoneNone
Rock SlideNoneNone90% > 100%NoneNone
Rock SmashNoneNoneNone50% > 100%None
Rock ThrowNoneNone90% > 100%NoneNone
Rock WreckerNoneNone90% > 100%NoneNone
Rolling KickNoneNone85% > 100%NoneNone
RoostNone10 > 5NoneNoneNone
Sacred FireNoneNone95% > 100%NoneNone
Sand TombNoneNone85% > 100%NoneNone
Sand-AttackNone15 > 5NoneNoneNone
Scale ShotNoneNone90% > 100%NoneNone
ScreechNone15 > 585% > 100%NoneNone
Seed FlareNoneNone85% > 90%NoneNone
SingNoneNone55% > 70%NoneNone
Skitter SmackNoneNone90% > 100%NoneNone
Sky AttackNoneNone90% > 100%NoneNone
Sky UppercutNoneNone90% > 100%NoneNone
SlamNoneNone75% > 90%NoneNone
Sleep PowderNoneNone75% > 80%NoneNone
SmogNoneNone70% > 90%40% > 100%None
SnarlNone15 > 1095% > 100%NoneNone
Sonic BoomNoneNone90% > 100%NoneNone
Spacial RendNoneNone95% > 100%NoneNone
Steam EruptionNoneNone95% > 100%NoneNone
Steel BeamNoneNone95% > 100%NoneNone
Steel WingNoneNone90% > 100%NoneNone
Stone EdgeNoneNone80% > 85%NoneNone
Strange SteamNoneNone95% > 100%NoneNone
Struggle BugNone20 > 10NoneNoneNone
Stun SporeNoneNone75% > 90%NoneNone
SubmissionNoneNone80% > 100%NoneNone
Super FangNoneNone90% > 100%NoneNormal > Dark
SupersonicNoneNone55% > 70%NoneNone
SwaggerNoneNone85% > 90%NoneNone
Sweet KissNoneNone75% > 80%NoneNone
Tail SlapNoneNone85% > 100%NoneNone
Take DownNoneNone85% > 100%NoneNone
Tearful LookNone20 > 10NoneNoneNone
ThunderNoneNone70% > 80%NoneNone
Thunder CageNoneNone90% > 100%NoneNone
Thunder FangNoneNone95% > 100%NoneNone
TickleNone20 > 10NoneNoneNone
WhirlpoolNoneNone85% > 100%NoneNone
WrapNoneNone90% > 100%NoneNone
Zen HeadbuttNoneNone90% > 100%NoneNone'''

lines = [line.strip() for line in data.strip().splitlines()]
for line in lines:
    parts = re.split(r'\t+', line)
    if len(parts) != 6:
        print('Bad line:', line)
        break
else:
    print('All good')
