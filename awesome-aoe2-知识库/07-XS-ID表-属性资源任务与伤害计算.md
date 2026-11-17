# XS 侧 ID 表：单位属性 211 / 资源 / 任务 / 伤害计算

> 出处：https://ugc.aoe2.rocks/general/  
> 源：仓库 `Divy1211/AoE2DE_UGC_Guide` 的原始 Markdown（docs/*.md），不是渲染后的 HTML  
> 抓取：2026-11-08  
> 这些 ID 同时是 `xsEffectAmount` / `xsSetAttribute` 与场景「修改属性」效果的入参

---

# 第一部分 单位属性 Attributes（211 条）

> 编号即属性 ID，写进 `xsEffectAmount(cSetAttribute, <单位ID>, <属性ID>, <值>, <玩家>)`。

*Written by: Alian713*

---

This page is a list of all the unit attributes that can be modified in the scenario editor and their purposes. If you know of any attributes that are not written on this page, or if the descriptions of the attributes are wrong, please let the authors of this guide know!

## 0. Hit Points

 - ID: 0

 - This attribute refers to the health of the units

## 1. Line of Sight

 - ID: 1

 - This is the distance a unit can see around itself

## 2. Garrison Capacity

 - ID: 2

 - This is the amount of units that can garrison inside another unit

## 3. Unit Size X

 - ID: 3

 - This determines the x-size of the unit's collision hitbox (width of the unit)

## 4. Unit Size Y

 - ID: 4

 - This determines the y-size of the unit's collision hitbox (length of the unit)

## 5. Movement Speed

 - ID: 5

 - This is the movement speed of a unit, measured in tiles per second

## 6. Rotation Speed

 - ID: 6

 - This is the rate at which units can rotate, measured in seconds per frame (this many seconds must pass before the object can switch to the next rotation frame). For example, for a trebuchet to start attacking a building facing the opposite direction, it has to rotate to face that way first

## 8. Armor

 - ID: 8

 - This is the quantity of armour a unit has on any of its `Armour Classes`. If you do not know what an `Armour Class` is, refer to the [Damage Calculation](../damage_calculation.md "Jump to: Game Mechanics > Damage Calculation") section of this guide. Note that changing the armour through this option will show it as being added to the base armour amount. (for example: 4+4)

## 9. Attack

 - ID: 9

 - This is the quantity of attack a unit has on any of its `Attack Classes`. If you do not know what an `Attack Class` is, refer to the [Damage Calculation](../damage_calculation.md "Jump to: Game Mechanics > Damage Calculation") section of this guide. Note that changing the attack through this option will show it as being added to the base attack amount. (for example: 6+2)

## 10. Attack Reload Time

 - ID: 10

 - This is the minimum time that must pass before a unit is able to fire another shot. For melee units it is the minimum time between two successive hits that they can do

## 11. Accuracy Percent

 - ID: 11

 - This determines how accurately a unit can aim at another unit

 - This accuracy is the accuracy of a unit to fire at the exact centre of its target. If the shot fired is not aimed at the exact centre of the target, it may still hit the target if its not off by too much since it can still land within the hitbox of the target, just not at the exact centre

    Thus, bigger targets are actually easier to hit, which explains why buildings are an easier target to hit for trebuchets than small units

    ![Visually Smaller](./imgs/visually_smaller.png "Targets that are farther away are visually smaller")

    In this image, you can see that shots that were fired in the red area in the 2nd scenario would've hit if the target had been closer like in the first scenario, but since the target is far away, they actually miss

    More technically, the visual angle of an object of the same size that is farther away is smaller, thus giving a smaller room for error for the shot in terms of the range of angles that will make the shot hit

    The chance of a unit getting converted by a monk is also determined by its accuracy

    If you modify an onager to have a big blast radius and give it a small accuracy, then attack a lot of units bunched together, the accuracy determines what percentage of units take damage from the blast of the onager! This is the reason why warwolf trebuchets get 100% accuracy because otherwise the blast wouldn't damage all of the units. Another interesting consequence of this is the delete trick with onagers and mangonels. This is where a mangonel is deleted immediately after it fires its shot and because a dead unit doesn't have an accuracy, it defaults to 100% and thus deals more damage to all the units in the blast radius

    Note: There are two other factors that play a role in determining the damage from the shot fired by the deleted mangonel

    1. The damage from a mangonel's shot is decreased over distance when moving outward from the centre of the blast (the targeted point). However, when the mangonel is deleted, this decrease over distance doesn't happen, and the projectile deals the full 100% damage to all the units in the blast radius!

    2. A shot that is fired from lower elevation would normally deal only 75% of its normal damage due to the elevation damage reduction. deleting a mangonel in this case also makes the damage the full 100% as if there was no elevation difference

## 12. Maximum Range

 - ID: 12

 - This is the maximum range of a unit. Note that to be able to shoot at a target, it must be visible to the unit via its own line of sight or from another unit's line of sight

## 13. Work Rate

 - ID: 13

 - This is the work rate for any unit that can do work. Villagers, Fishing Ships, Serjeants

## 14. Carry Capacity

 - ID: 14

 - This is the carry capacity of Villagers

## 15. Base Armor

 - ID: 15

 - This is the quantity of base armour a unit has on any of its `Armour Classes`. If you do not know what an `Armour Class` is, refer to the [Damage Calculation](../damage_calculation.md "Jump to: Game Mechanics > Damage Calculation") section of this guide. Note that changing the armour through this option will show it as the base armour itself, and it will not be added to the regular amount

## 16. Projectile Unit

 - ID: 16

 - This is the ID of the projectile that a unit fires

## 17. Building Icon Override

 - ID: 17

 - The functionality of this attribute is unknown as it doesn't always behave certainly. If you know what this attribute does, please let the authors of this guide know!

## 18. Terrain Defense Bonus

 - ID: 18

 - Unknown... What does this attribute do?

## 19. Projectile Smart Mode

 - ID: 19

 - This is a combinable bit field. Controls the following two behaviours for projectiles:

 - For example, if we set this property of the projectile used by an archer to `1`, it will have ballistics. (This is exactly what researching ballistics does in the first place). If we set this property to `2`, a missed projectile that hits another unit will deal its full damage instead of the 50% that it would normally do

    What if we want to enable both properties at once? This is achieved by adding the flag values for both of them together. Setting this property to `3` enables both effects

    | Property | Flag Value |
    | :- | -: |
    | No Ballistics | 0 |
    | Has Ballistics | 1 |
    | Deals full damage on missed hit | 2 |

## 20. Minimum Range

 - ID: 20

 - The minimum distance a unit must be from an attacking unit for the attacking unit to be able to fire its projectile

## 21. Amount of 1st Resource Storage

 - ID: 21

 - This is the amount of 1st resource contained in any unit. Refer to A.G.E. to see which resource this is for each unit

## 22. Blast Width

 - ID: 22

 - All enemy units inside this radius take damage from an attacking unit. This is used by elephants, Druzhina Halberdiers, and Logistica Cataphracts

## 23. Search Radius

 - ID: 23

 - The maximum distance at which a unit can detect and auto attack enemy units

## 24. Bonus Damage Resistance

 - ID: 24

 - Used by Sicilians for the 33% bonus damage resistance. Set to 0.33 for all Sicilian land military units except siege

 - Do not make it greater than 1

## 25. Icon ID

 - ID: 25

 - The ID of the icon that you want a unit to show

## 26. Amount of 2nd Resource Storage

 - ID: 26

 - This is the amount of 2nd resource contained in any unit. Refer to A.G.E. to see which resource this is for each unit

## 27. Amount of 3rd Resource Storage

 - ID: 27

 - This is the amount of 3rd resource contained in any unit. Refer to A.G.E. to see which resource this is for each unit

## 28. Fog Visibility

 - ID: 28

 - Controls visibility of a unit through the fog of war

    | Property | Flag Value |
    | :- | -: |
    | Not Visible | 0 |
    | Always Visible | 1 |
    | Visible If Alive | 2 |
    | Inverted Visibility | 3 |
    | Check Doppelganger | 4 |

## 29. Occlusion Mode

 - ID: 29

 - This is a combinable bit field. Controls the outlines of units as seen through other units

    | Property | Flag Value |
    | :- | -: |
    | No outline | 0 |
    | Display outline when behind other units that have flag 2 | 1 |
    | Other units' outlines are rendered when they are behind this unit | 2 |
    | Display outline on this unit's foundation when behind other units that have flag 2 | 4 |

## 30. Garrison Type

 - ID: 30

 - This is a combinable bit field. Controls which units are able to garrison in a building. A unit needs to have the garrison in building task to be able to garrison in a building to begin with

    | Property | Flag Value |
    | :- | -: |
    | Villagers | 1 |
    | Infantry | 2 |
    | Cavalry | 4 |
    | Monks | 8 |
    | Herdables | 16 |
    | Siege | 32 |
    | Ships | 64 |

## 32. Unit Size Z

 - ID: 32

 - This determines the z-size of the unit's collision hitbox (height of the unit)

 - Setting this to 0 allows other units to walk over this unit

    Does this still control the HP bar location as specified in A.G.E.?

## 33. Can Be Built On

 - ID: 33

 - Determines if a building foundation can be placed on top of a unit

    | Property | Flag Value |
    | :- | -: |
    | Disallow unit to be built on. This is the value for almost all units | 0 |
    | Allow unit to be built on. This is the value for corpses, rubble, eye candy | 1 |

## 34. Foundation Terrain

 - ID: 34

 - This is the ID of the terrain created under a building when its construction is finished

 - Only affects units of Type 80 (Building)



    | Property | Flag Value |
    | :- | -: |
    | No terrain change | -1 |

## 40. Hero Status

 - ID: 40

 - This is a combinable bit field. Controls the following properties:

 - For example, if we set the hero status of a knight to 2, a monk will not be able to convert it. If we set the hero status of a militia to 4, it will regenerate HP automatically

    What if we want to enable multiple properties at once? This is achieved by adding the flag values for those properties together and setting the hero status to that value. For example, if we want to make a paladin both unconvertable and regenerate HP automatically, we can set its hero status to 2+4 = 6. This means that the hero status of a unit can take on any values in the range 1-63. If you set it to any other value, it does not have any effect on the unit

    This works because notice that there is one and only one way to add different flag values together to obtain a particular value for the hero status! For example, if we have a value of 20 for the hero status of a unit, the only way to make 20 from the above flag values is to add 4 and 16. Thus, we know that the properties corresponding to the flag values 4 (self regeneration) and 16 (protected formation by default) must be enabled for that unit

    This is a consequence of the fact that every number can be represented as a unique sum of powers of two (binary numbers)

    | Property | Flag Value |
    | :- | -: |
    | Full Hero Status | 1 |
    | Cannot be Converted | 2 |
    | Self Regeneration (30 HP/min) | 4 |
    | Defensive Stance by Default | 8 |
    | Protected Formation by Default | 16 |
    | Safe Delete Confirmation | 32 |
    | Hero Glow | 64 |
    | Invert All Flags (except flag 1) | 128 |

## 41. Frame Delay

 - ID: 41

 - The amount of delay between the point when the attacking animation starts and the actual hit happening for military units. This is what makes Cavalry Archers annoying to micro

## 42. Train Location

 - ID: 42

 - The ID of the unit that trains any given unit. Barracks train Militia, so the train location of a Militia is the ID of the Barracks

## 43. Train Button

 - ID: 43

 - The button used for training any given unit. For example, Militia are trained by using the first button, hence the Button Location of Militia is 1. This number ranges from 0-15

## 44. Blast Attack Level

 - ID: 44

 - A unit deals blast damage to ***other*** units with ***equal or higher*** [Blast Defense Level](./#45-blast-defense-level "Jump to: Blast Defense Level") that are in its blast radius. For example, while mangonels (blast attack: 2) can damage your own units (blast defense of all player owned units is always 2), scorpions (blast attack: 3) cannot do the same

 - One of the flags 0-3 can be combined with the combinable flags 4 to 128 by adding the two values

    | Property | Flag Value |
    | :- | -: |
    | Damage resources, nearby allied units and tress | 0 |
    | Damage trees, nearby allied units | 1 |
    | Damage nearby and allied units | 2 |
    | Damage targeted unit only | 3 |
    | Damage enemy units only | 4 |
    | Ignore friendly fire | 8 |
    | Unused | 16 |
    | Unused | 32 |
    | Attenuate damage as distance from the centre of attack increases (infantry only) | 64 |
    | Blast damage is dealt along the direction the unit is facing only. This area is a very narrow cone | 128 |

## 45. Blast Defense Level

 - ID: 45

 - A unit feels the blast damage from ***other*** units with ***equal or lower*** [Blast Attack Level](./#44-blast-attack-level "Jump to: Blast Attack Level") and if it is inside the attacker's blast radius. For example, while onagers (blast attack: 1) can cut trees (blast defense 1), mangonels (blast attack: 2) cannot do the same

    | Property | Flag Value |
    | :- | -: |
    | damage resources, nearby allied units and tress | 0 |
    | damage trees, nearby allied units | 1 |
    | damage nearby allied units | 2 |
    | damage targeted unit only | 3 |

## 46. Shown Attack

 - ID: 46

 - The amount of attack that is displayed as a unit's attack (may not actually be the true attack)

## 47. Shown Range

 - ID: 47

 - The quantity that is displayed as a unit's attack ingame (may not actually be the true attack)

## 48. Shown Melee Armor

 - ID: 48

 - The quantity that is displayed as a unit's melee armour ingame (may not actually be the true armour)

## 49. Shown Pierce Armor

 - ID: 49

 - The quantity that is displayed as a unit's pierce armour ingame (may not actually be the true armour)

## 50. Object Name ID

 - ID: 50

 - The string ID to use for the name of an object. A string ID is used for refering to strings that the game recognises by default. It can be used to automatically set names by using a value that the game recognises. Trying out the value 1 on a unit and seeing what happens is left as an excersise for the reader

## 51. Short Description ID

 - ID: 51

 - The string ID for the Short Description of an object. A string ID is used for refering to strings that the game recognises by default. It can be used to automatically set a Short Description by using a value that the game recognises. Trying out the value 1 on a unit and seeing what happens is left as an excersise for the reader

## 53. Terrain Restriction ID

 - ID: 53

 - This number determines how a unit interacts with terrains and which terrains it can walk on

    | Property | Flag Value |
    | :- | -: |
    | All | 0 |
    | Land And Shallows | 1 |
    | Beach | 2 |
    | Water Small Trail | 3 |
    | Land | 4 |
    | Nothing | 5 |
    | Water No Trail | 6 |
    | All Except Water | 7 |
    | Land Except Farm | 8 |
    | Nothing 2 | 9 |
    | Land And Beach | 10 |
    | Land Except Farm 2 | 11 |
    | All Except Water Bridge Cannon | 12 |
    | Water Medium Trail | 13 |
    | All Except Water Bridge Arrow | 14 |
    | Water Large Trail | 15 |
    | Grass And Beach | 16 |
    | Water And Bridge Except Beach | 17 |
    | All Except Water Bridge Spear | 18 |
    | Only Water And Ice | 19 |
    | All Except Water Wheel | 20 |
    | Shallow Water | 21 |
    | All Dart | 22 |
    | All Arrow Fire | 23 |
    | All Cannon Fire | 24 |
    | All Spear Fire | 25 |
    | All Dart Fire | 26 |
    | All Laser | 27 |
    | All Except Water Cavalry | 28 |
    | All Except Water Packet Trebuchet | 29 |
    | Water Smallest Trail | 30 |

## 54. Unit Trait

 - ID: 54

 - This is a combinable bit field. Controls the following properties:

 - See Also:

    [Trait Piece](./#56-trait-piece)

    | Property | Flag Value |
    | :- | -: |
    | Garrison Unit | 1 |
    | Ship Unit | 2 |
    | Build Another Building (Serjeants) [See Special Ability: Mode 7] | 4 |
    | Transform Into Another Unit (Ratha) | 8 |
    | Auto Scout Unit | 16 |

## 56. Trait Piece

 - ID: 56

 - This can be set to the ID of a unit that is used along with some of the Unit Traits

 - See Also:

    [Unit Trait](./#54-unit-trait)

    | Property | Flag Value |
    | :- | -: |
    | Unused | 1 |
    | Unused | 2 |
    | Build Unit | 4 |
    | Transform Unit | 8 |
    | Unused | 16 |

## 57. Dead Unit ID

 - ID: 57

 - This is the ID of the unit to spawn after the current unit dies. This is whats used to make the dismounted konniks possible

## 58. Hotkey ID

 - ID: 58

 - This number determines which hotkey is assigned to a unit

## 59. Maximum Charge

 - ID: 59

 - The maximum amount of charge that a unit can hold

## 60. Recharge Rate

 - ID: 60

 - The rate of charge regeneration per second

## 61. Charge Event

 - ID: 61

 - This action depletes the unit's charge

    | Property | Flag Value |
    | :- | -: |
    | 1 - Deplete charge, 0 - Keep charge | Charge Type one of `1`, `2`, or `3` |
    | Max range modifier | Charge Type one of `6`, or `7` |
    | 0 - Transform unit until one attack, -1 - perform attack ground on it's location | Charge Type is `-1` |
    | 0 - Transform unit until one attack | Charge Type is `-2` |
    | Aura task duration | Charge Type is `-3` |
    | Conversion range (maybe overridden by conversion tasks) | Charge Type is `-4` |

## 62. Charge Type

 - ID: 62

 - The type of charge that a unit holds

    | Property | Flag Value |
    | :- | -: |
    | Spawn Building on top of the unit (Uses unit set in Trait Piece) | -5 |
    | Conversion ability (Needs task 104). Charge Target defines the conversion percent chance | -4 |
    | Active aura ability (Needs task 155 with unused flag 8 set) | -3 |
    | Active targetted transform (Uses unit set in Trait Piece). If charge target = -1, use attack ground targetting | -2 |
    | Active temporary transform (Uses unit set in Trait Piece) | -1 |
    | Attack charge | 1 |
    | ??? charge | 2 |
    | Area attack charge | 3 |
    | Agility charge | 4 |
    | Ignore Melee Attack | 5 |
    | Fire only Charge projectiles, sets Total Projectiles to the value of Max Total Projectiles (Lou Chuan) | 6 |
    | Fires 1 Charge projectile and additional Secondary Projectiles, sets Total Projectiles to the value of Max Total Projectiles | 7 |

## 63. Combat Ability

 - ID: 63

 - Combinable bit field. Controls several attacking behaviours for units

    | Property | Flag Value |
    | :- | -: |
    | Ignore melee and pierce armours of the targeted unit | 1 |
    | Resist armour-ignoring attacks | 2 |
    | Damage the targeted unit's melee and pierce armors by 1, for a minimum of 0 (Obuch) | 4 |
    | Attack ground ability | 8 |
    | Bulk volley release (kipchak/siege weapons) | 16 |
    | Enable aura ability (task 155) (Stronghold castle/Caravanserai/Centurion) | 32 |
    | Invert aura ability (task 155) to boost self (Monaspa) - Auto Search = 1 needed for multiple tasks | 64 |
    | Activate stringer ability (task 157) | 128 |

## 64. Attack Dispersion

 - ID: 64

 - Half of the radius from the target unit in which missed projectiles fired by this unit can land in

## 65. Secondary Projectile Unit

 - ID: 65

 - This is the ID of the secondary projectile that a unit fires (Chu Ko Nu)

## 66. Blood Unit

 - ID: 66

 - This is the ID of a secondary unit to spawn after the current unit dies. This could potentially be used along with dead unit ID to spawn two units after a single unit dies

## 67. Projectile Hit Mode

 - ID: 67

 - Controls how a projectile collides with units in the path of its target. Currently changing this through XS has no effect

    | Property | Flag Value |
    | :- | -: |
    | Collide only with the targeted unit | 0 |
    | Collide with any damage-able units in the path to the targetted unit | 1 |
    | Collide with any unit in the path to the targetted unit | 2 |

## 68. Projectile Vanish Mode

 - ID: 68

 - Controls if a projectile passes through or disappears on impact. Currently changing this through XS has no effect

    | Property | Flag Value |
    | :- | -: |
    | Disappear on first impact | 0 |
    | Pass through | 1 |
    | Always spawn a dead unit | 2 |

## 69. Projectile Arc

 - ID: 69

 - Controls the maximum height of the fired projectile

## 70. Attack Graphic

 - ID: 70

 - Controls the Attack Graphic

## 71. Standing Graphic

 - ID: 71

 - The sprite animation shown when a unit is idle

 - Units randomly choose between this or Standing Graphic 2

## 72. Standing Graphic 2

 - ID: 72

 - The sprite animation shown when a unit is idle

 - Units randomly choose between this or Standing Graphic

## 73. Dying Graphic

 - ID: 73

 - The sprite animation shown when a unit dies

## 74. Undead Graphic

 - ID: 74

 - This graphic is shown after a unit's dying animation instead of replacing it with its dead unit if its "Undead Mode" is set to `1`. Used to assign decay graphic to units without "Undead Mode" set to 1. Overrides the standing graphic of the object's dead unit

 - Depends on Undead Mode flag

## 75. Walking Graphic

 - ID: 75

 - The sprite animation shown when a unit is walking

## 76. Running Graphic

 - ID: 76

 - The sprite animation shown when a unit is running

 - A unit runs when it is issued an attack command, or when a unit is fleeing (deer-like units)

    Most units do not have a running graphic

    A graphic can multiply the speed of the unit it is applied to

    This is used for deer, wolves, boars, etc. when they are issued an attack command

## 77. Special Graphic

 - ID: 77

 - This sprite animation is shown  when a unit uses one of "Block", "Charge", or "Counter Charge" special abilities

 - Special abilities are an unused feature in AoE2, they were planned but never made it into AoK

## 78. Obstruction Type

 - ID: 78

 - Controls unit outline and collision

    | Property | Flag Value |
    | :- | -: |
    | Square outline, and passable | 0 |
    | Same as 0 | 1 |
    | Solid square outline, and has collision box | 2 |
    | Square outline, and has collision box | 3 |
    | No outline, and passable | 4 |
    | Round outline, and has collision box | 5 |
    | Same as 2, but designed for mountains | 10 |
    | Consider the selection size of a radius entirely as opposed to the actual defined collision size | 11 |
    | Ignore hard obstructions entirely and just consider the space occupied with no obstruction at all | 12 |
    | Consider the selection radius when placing other objects, but use the original obstruction size for hard obstructions | 13 |

## 79. Blockage Class

 - ID: 79

 - Controls unit blockage class

    | Property | Flag Value |
    | :- | -: |
    | Forces default obstruction type | 0 |
    | Resource | 1 |
    | Unit | 2 |
    | Building | 3 |
    | Wall | 4 |
    | Gate, allows trespassing | 5 |
    | Cliff, blocks walling | 6 |

## 80. Selection Effect

 - ID: 80

 - Controls unit hit point bar and outline

    | Property | Flag Value |
    | :- | -: |
    | Has hit point bar | 0 |
    | Has hit point bar, and outline | 1 |
    | No hit point bar, or outline | 2 |
    | No hit point bar, but has outline | 3 |

## 81. Special Ability

 - ID: 81

 - Enables certain special abilities

    | Property | Flag Value |
    | :- | -: |
    | Enable charge attack ability (task 133) | 3 |

## 82. Idle Attack Graphic

 - ID: 82

 - TODO

## 83. Hero Glow Graphic

 - ID: 83

 - TODO

## 84. Garrison Graphic

 - ID: 84

 - TODO

## 85. Construction Graphic

 - ID: 85

 - TODO

## 86. Snow Graphic

 - ID: 86

 - TODO

## 87. Destruction Graphic

 - ID: 87

 - TODO

## 88. Destruction Rubble Graphic

 - ID: 88

 - TODO

## 89. Researching Graphic

 - ID: 89

 - TODO

## 90. Research Completed Graphic

 - ID: 90

 - TODO

## 91. Damage Graphic

 - ID: 91

 - TODO

## 92. Selection Sound

 - ID: 92

 - TODO

## 93. Selection Sound Event

 - ID: 93

 - TODO

## 94. Dying Sound

 - ID: 94

 - TODO

## 95. Dying Sound Event

 - ID: 95

 - TODO

## 96. Train Sound

 - ID: 96

 - TODO

## 97. Train Sound Event

 - ID: 97

 - TODO

## 98. Damage Sound

 - ID: 98

 - TODO

## 99. Damage Sound Event

 - ID: 99

 - TODO

## 100. Resource Costs

 - ID: 100

 - Refers to the first resource cost of a unit. Refer to A.G.E. to see which resource cost that is

## 101. Train Time

 - ID: 101

 - This is the amount of time it takes to create a unit

## 102. Total Missiles

 - ID: 102

 - This is the number of projectiles a unit fires. The Chu Ko Nu fires 3 and the Elite Chu Ko Nu fires 5

## 103. Food Costs

 - ID: 103

 - The food cost of a unit

## 104. Wood Costs

 - ID: 104

 - The wood cost of a unit

## 105. Gold Costs

 - ID: 105

 - The gold cost of a unit

## 106. Stone Costs

 - ID: 106

 - The stone cost of a unit

## 107. Maximum Total Missiles

 - ID: 107

 - The maximum number of projectiles a unit can fire when other units are garrisoned inside of it. A castle fires 5 projectiles by default but can fire more if units are garrisoned inside it. This attribute controls the maximum number of those

## 108. Garrison Heal Rate

 - ID: 108

 - The rate measured in HP/s at which garissoned units are healed inside a given building

## 109. Regeneration Rate

 - ID: 109

 - The rate measured in HP/minute at which units heal themselves. This value is overridden to 30 HP/minute if the flag for Self Regeneration is set in the [Hero Status](./#40-hero-status "Jump to: 26. Hero Status") of a unit

## 110. Population

 - ID: 110

 - Modifies the population headroom storage of a unit. Negative values = require population (units), positive values = give population (houses). This is not a real attribute that exists in A.G.E., just seems like a way to edit the population heardroom provided by a unit

## 111. Minimum Conversion Time Modifier

 - ID: 111

 - Adds to the minimum time required to convert the unit

 - By default, units have a 4 monk second minimum conversion time

    The overall minimum conversion time for all units is also affected by [Convert Resist Min Adjustment](../../resources/resources/#178-convert-resist-min-adjustment)

## 112. Maximum Conversion Time Modifier

 - ID: 112

 - Adds to the maximum time after which a unit conversion is forced

 - By default, units have a 10 monk second maximum conversion time

    The overall maximum conversion time for all units is also affected by [Convert Resist Max Adjustment](../../resources/resources/#179-convert-resist-max-adjustment)

## 113. Conversion Chance Modifier

 - ID: 113

 - The probability of conversion every monk second is divided by this value for the unit

 - The overall conversion probability for all units is also affected by [Conversion Resistance](../../resources/resources/#77-conversion-resistance)

## 114. Formation Category

 - ID: 114

 - Control where the units in formation

    | Property | Flag Value |
    | :- | -: |
    | Not using formation | 0 |
    | Mobile | 1 |
    | Body | 2 |
    | Ranged | 3 |
    | Long Ranged | 4 |
    | Protected | 5 |

## 115. Area Damage

 - ID: 115

 - Blast damage multiplier to non directly targeted units. Blast damage to non directly targeted units is a fixed value if this is negative

## 118. Damage Reflection

 - ID: 118

 - Damage percentage of the received damage to be reflected on the attacker (only for melee damage)

## 119. Friendly Fire Damage

 - ID: 119

 - Blast damage multiplier to non directly targeted units. Blast damage to non directly targeted units is a fixed value if this is negative

## 120. Regeneration HP Percent

 - ID: 120

 - Percentage of the unit’s max HP that is regenerated over a minute

## 121. Ability Button Icon ID

 - ID: 121

 - Override for Transform/Active Ability Icon. Uses ID from `Materials.json`

## 122. Ability Short Tooltip ID

 - ID: 122

 - Override for Transform/Active Ability Short Tooltip

## 123. Ability Extended Tooltip ID

 - ID: 123

 - Override for Transform/Active Ability Long Tooltip

## 124. Ability Hotkey Action

 - ID: 124

 - `button_action_list` when pressing button/hotkey for the ability or transformation

## 125. Charge Projectile Unit

 - ID: 125

 - Blast damage multiplier to non directly targeted units. Blast damage to non directly targeted units is a fixed value if this is negative

## 126. Available Unit Flag

 - ID: 126

 - When Disabled flag 2 or 4 is set, sets value for number of trainable unit. Will use units paired in `LinkedUnits.json` to count them together

## 127. Disabled Unit Flag

 - ID: 127

 - Enable/Disable a unit

    | Property | Flag Value |
    | :- | -: |
    | Disabled | 1 |
    | Limited training. Cannot be retrained after death | 2 |
    | Limited training. Can be retrained after death | 4 |

## 128. Attack Priority

 - ID: 128

 - Defines what type of target the unit will prioritize

    | Property | Flag Value |
    | :- | -: |
    | Units > Buildings | 1 |
    | Buildings > Units | 2 |
    | Buildings only | 3 |

## 129. Invulnerability Level

 - ID: 129

 - Sets an HP threshold after which a unit no longer receives damage when attacked

    | Property | Flag Value |
    | :- | -: |
    | Multiplier of Base HP | > 0 |
    | Fixed value of HP |  0 |
    | Flat dps value added to the unit’s dps | < 0 |

## 131. Attack Graphic 2

 - ID: 131

 - Second attack graphic of the unit; alternates with the first attack graphic when assigned

## 132. Command Sound

 - ID: 132

 - TODO

## 133. Command Sound Event

 - ID: 133

 - TODO

## 134. Move Sound

 - ID: 134

 - TODO

## 135. Move Sound Event

 - ID: 135

 - TODO

## 136. Construction Sound

 - ID: 136

 - TODO

## 137. Construction Sound Event

 - ID: 137

 - TODO

## 138. Transform Sound

 - ID: 138

 - TODO

## 139. Transform Sound Event

 - ID: 139

 - TODO

## 140. Run Pattern

 - ID: 140

 - TODO

## 141. Interface Kind

 - ID: 141

 - TODO

## 142. Combat Level

 - ID: 142

 - TODO

## 143. Interaction Mode

 - ID: 143

 - TODO

## 144. Minimap Mode

 - ID: 144

 - TODO

## 145. Trailing Unit

 - ID: 145

 - TODO

## 146. Trail Mode

 - ID: 146

 - TODO

## 147. Trail Density

 - ID: 147

 - TODO

## 148. Projectile Graphic Displacement X

 - ID: 148

 - TODO

## 149. Projectile Graphic Displacement Y

 - ID: 149

 - TODO

## 150. Projectile Graphic Displacement Z

 - ID: 150

 - TODO

## 151. Projectile Spawning Area Width

 - ID: 151

 - TODO

## 152. Projectile Spawning Area Length

 - ID: 152

 - TODO

## 153. Projectile Spawning Area Randomness

 - ID: 153

 - TODO

## 154. Damage Graphics Entry Mod

 - ID: 154

 - Determines the index at which damage graphic/damage graphic percent/damage graphic apply mode values are changed via effects in XS.

 - - Multiply by N to insert a new entry at index N, and then set entry mod to N

    - Multiply by -(N+1) to delete index N, and then set entry mod to N

    - Multiply with 255 (32767 also works) to append an entry at the end, and set the entry mod to the last index

    - Multiply with -255 (-32768 also works) to delete the index at the end, and set entry mod to the new last index

    - Note that inserting a new entry copies the existing last entry in the list as the default

## 155. Damage Graphics Total Num

 - ID: 155

 - The length of the damage sprites list. Can be set to shrink/extend the list (duplicates the last entry when extending).

## 156. Damage Graphic Percent

 - ID: 156

 - The damage percent at which this sprite starts to be applied. This sprite remains active until the damage percent of the next damage sprite entry

## 157. Damage Graphic Apply Mode

 - ID: 157

 - The apply mode for this damage sprite.

 - - 0: Overlay flames on building

    - 1: Overlay randomly

    - 2: Replace (walls)

## 158. Train Locations Entry Mod

 - ID: 158

 - Determines the index at which train location/train button/train time/hotkey values are modified via effects in XS.

 - - Multiply by N to insert a new entry at index N, and then set entry mod to N

    - Multiply by -(N+1) to delete index N, and then set entry mod to N

    - Multiply with 32767 to append an entry at the end, and set the entry mod to the last index

    - Multiply with -32768 to delete the index at the end, and set entry mod to the new last index

    - Note that inserting a new entry copies the existing last entry in the list as the default

## 159. Train Locations Total Num

 - ID: 159

 - The length of the train locations list. Can be set to shrink/extend the list (duplicates the last entry when extending).

## 160. Add Armor Type

 - ID: 160

 - Setting this creates a new armor class in the targeted object/unit

 - Note: You still need to set the value of the class using the regular damage class modification effect.

## 161. Add Attack Type

 - ID: 161

 - Setting this creates a new attack class in the targeted object/unit

 - Note: You still need to set the value of the class using the regular damage class modification effect.

## 162. Charge Target

 - ID: 162

 - TODO

## 163. Size Class

 - ID: 163

 - Controls garrison type properties

 - - 0: Legacy object_group dependent behaviour

    - 1: Civilian

    - 2: Infantry

    - 3: Cavalry

    - 4: Religious

    - 5: Livestock

    - 6: Siege

    - 7: Ships

    - 8: Unused

## 164. Remove Armor Type

 - ID: 164

 - Setting this removes an existing armor class in the targeted object/unit

## 165. Remove Attack Type

 - ID: 165

 - Setting this removes an existing attack class in the targeted object/unit

## 166. Undead Flag

 - ID: 166

 - Changes behaviour related to death of an object

    | Property | Flag Value |
    | :- | -: |
    | Default | 0 |
    | Show Undead Graphic | 1 |
    | Ignore In Kill Stats | 2 |
    | Garrison Invincibility | 4 |

## 167. Build And Go Away

 - ID: 167

 - When set, removes this building after it is built

## 168. Type First Storage

 - ID: 168

 - The resource ID of the first attribute storage

## 169. Type Second Storage

 - ID: 169

 - The resource ID of the second attribute storage

## 170. Type Third Storage

 - ID: 170

 - The resource ID of the third attribute storage

## 171. Store Flag First Storage

 - ID: 171

 - The store flag of the first attribute storage

## 172. Store Flag Second Storage

 - ID: 172

 - The store flag of the second attribute storage

## 173. Store Flag Third Storage

 - ID: 173

 - The store flag of the third attribute storage

## 174. Amount First Cost

 - ID: 174

 - The amount for the first cost

## 175. Amount Second Cost

 - ID: 175

 - The amount for the second cost

## 176. Amount Third Cost

 - ID: 176

 - The amount for the third cost

## 177. Type First Cost

 - ID: 177

 - The type of first cost

## 178. Type Second Cost

 - ID: 178

 - The type of second cost

## 179. Type Third Cost

 - ID: 179

 - The type of third cost

## 180. Deduct Flag First Cost

 - ID: 180

 - The deduct flag for the first cost

## 181. Deduct Flag Second Cost

 - ID: 181

 - The deduct flag for the second cost

## 182. Deduct Flag Third Cost

 - ID: 182

 - The deduct flag for the third cost

## 183. Spawning Graphic

 - ID: 183

 - The graphic shown when a unit spawns

## 184. Upgrade Graphic

 - ID: 184

 - The graphic shown when a unit upgrades

## 185. Fly Mode

 - ID: 185

 - Unknown

    | Property | Flag Value |
    | :- | -: |
    | All units | 0 |
    | All projectiles | 1 |

## 186. Can Be Gathered

 - ID: 186

 - For tracking gatherable resources. Unknown

    | Property | Flag Value |
    | :- | -: |
    | All units | 0 |
    | Resources like gold/stone etc. | 1 |

## 187. Hill Mode

 - ID: 187

 - Building placement restrictions around hills

    | Property | Flag Value |
    | :- | -: |
    | No Restriction (Farms) | 0 |
    | No Corners of Hills (Unused) | 1 |
    | Flat Only (TCs) | 2 |
    | Allows One Elevation Difference (Most Buildings) | 3 |

## 188. Doppelganger

 - ID: 188

 - Unknown

## 189. Gather Group

 - ID: 189

 - Unknown

## 190. Task Swap Group

 - ID: 190

 - Controls which units can swap with each other when attempting to find a valid task from all their task lists

    | Property | Flag Value |
    | :- | -: |
    | None | 0 |
    | Male Villagers | 1 |
    | Female Villagers | 2 |
    | Fishing Ships | 3 |

## 191. Placement Terrain1

 - ID: 191

 - Restricts placement on one of these two terrains

## 192. Placement Terrain2

 - ID: 192

 - Restricts placement on one of these two terrains

## 193. Placement Center Terrain 1

 - ID: 193

 - Restricts placement such that the anchor tile of the unit must be on one of these two terrains

## 194. Placement Center Terrain 2

 - ID: 194

 - Restricts placement such that the anchor tile of the unit must be on one of these two terrains

## 195. Initiated Tech Id

 - ID: 195

 - Initiates this technology on being built

## 196. Min Size Multiplier

 - ID: 196

 - Unknown

## 197. Selection Outline Size X

 - ID: 197

 - The size of the selection outline along X

## 198. Selection Outline Size Y

 - ID: 198

 - The size of the selection outline along Y

## 199. Selection Outline Size Z

 - ID: 199

 - The size of the selection outline along Z.

## 200. Clearance Size X

 - ID: 200

 - Unknown

## 201. Clearance Size Y

 - ID: 201

 - Unknown

## 202. Stack Unit

 - ID: 202

 - Additional unit placed directly on top of this unit

## 203. Head Unit

 - ID: 203

 - The unit that annexes get attached to

## 204. Transform Unit

 - ID: 204

 - Unpacks into this unit

## 205. Pile Unit

 - ID: 205

 - Additional blood unit that only appears when a building is destroyed but not when deleted

## 206. Annex Unit 1

 - ID: 206

 - First annex unit

## 207. Annex Unit 2

 - ID: 207

 - Second annex unit

## 208. Annex Unit 3

 - ID: 208

 - Third annex unit

## 209. Annex Unit 4

 - ID: 209

 - Fourth annex unit

## 210. Annex Unit 1 Offset X

 - ID: 210

 - Offset for the first annex unit from the main unit along the X direction

## 211. Annex Unit 1 Offset Y

 - ID: 211

 - Offset for the first annex unit from the main unit along the Y direction

## 212. Annex Unit 2 Offset X

 - ID: 212

 - Offset for the second annex unit from the main unit along the X direction

## 213. Annex Unit 2 Offset Y

 - ID: 213

 - Offset for the second annex unit from the main unit along the Y direction

## 214. Annex Unit 3 Offset X

 - ID: 214

 - Offset for the third annex unit from the main unit along the X direction

## 215. Annex Unit 3 Offset Y

 - ID: 215

 - Offset for the third annex unit from the main unit along the Y direction

## 216. Annex Unit 4 Offset X

 - ID: 216

 - Offset for the fourth annex unit from the main unit along the X direction

## 217. Annex Unit 4 Offset Y

 - ID: 217

 - Offset for the fourth annex unit from the main unit along the Y direction

## 218. Move Algorithm

 - ID: 218

 - Unknown

## 219. Spacing Modifier

 - ID: 219

 - Unknown

## 220. Can Burn

 - ID: 220

 - Gives flames to buildings when set to 1 when damaged. Unknown

## 221. Gather Flag

 - ID: 221

 - For resources, similar to Can Be Gathered. Unknown

---

# 第二部分 资源 Resources

> 编号即资源 ID，与 .dat 的 resource id 同一套。

# Player Resources

*Written by: Alian713, Bradical, & Kramb*

---

This page is a list of all the player resources in the scenario editor and their purposes. If you know of any resources that are not written on this page, or if the descriptions of the resources are wrong, please let the authors of this guide know!

## 0. !Food Storage

- ID: 0

- Purpose: Current food amount

## 1. !Wood Storage

- ID: 1

- Purpose: Current wood amount

## 2. !Stone Storage

- ID: 2

- Purpose: Current stone amount

## 3. !Gold Storage

- ID: 3

- Purpose: Current gold amount

## 4. Population Headroom

- ID: 4

- Purpose: Amount of free population space. Note that this is NOT the population cap

## 5. Conversion Range

- ID: 5

- Purpose: Unknown... What does this resource do?

## 6. Current Age

- ID: 6

- Purpose: Controls the age name and icon at the top of the screen

- Default Values:

    - 0:  Dark Age
    - 1:  Feudal Age
    - 2:  Castle Age
    - 3:  Imperial Age

- Note: Setting this to an amount higher than 3 cycles the icon but keeps the age at imperial

## 7. Relics Captured

- ID: 7

- Purpose: Number of relics held

## 8. Enable Sun Ce Building Conversion (Unused Resource 08)

- ID: 8

- Purpose: Enables `Sun Ce` to convert buildings

- Default Values:

    - 0:  No (default)
    - 1:  Yes
    - $\geq$2: Sun Ce can convert buildings from range

- Note: The editor name of the resource is incorrect

## 9. Trade Goods

- ID: 9

- Purpose: Unused

## 10. Unused Resource 10

- ID: 10

- Purpose: Unused

## 11. Current Population

- ID: 11

- Purpose: The current population

## 12. Corpse Decay Time

- ID: 12

- Purpose: Unknown... What does this resource do?

## 13. Remarkable Discovery

- ID: 13

- Purpose: Unknown... What does this resource do?

## 14. Monuments Captured

- ID: 14

- Purpose: Number of monuments owned

## 15. Meat Storage

- ID: 15

- Purpose: Unknown... What does this resource do?

## 16. Berry Storage

- ID: 16

- Purpose: Unknown... What does this resource do?

## 17. Fish Storage

- ID: 17

- Purpose: Unknown... What does this resource do?

## 18. Civilization Voice Override

- ID: 18

- Purpose: Allows overriding a civilization's voice lines with another civ

## 19. Total Units Owned

- ID: 19

- Purpose: Total units owned, excluding buildings

## 20. Units Killed

- ID: 20

- Purpose: Total units killed, excluding buildings

## 21. Technology Count

- ID: 21

- Purpose: Number of technologies researched till now

## 22. % Map Explored

- ID: 22

- Purpose: Percentage of the map explored

## 23. Castle Age Tech ID

- ID: 23

- Purpose: Always 102

- Note: Nothing happens when you change this, probably for mods only

## 24. Imperial Age Tech ID

- ID: 24

- Purpose: Always 103

- Note: Nothing happens when you change this, probably for mods only

## 25. Feudal Age Tech ID

- ID: 25

- Purpose: Always 101

- Note: Nothing happens when you change this, probably for mods only

## 26. Attack Warning Sound ID

- ID: 26

- Purpose: Always 0

- Note: Nothing happens when you change this, probably for mods only

## 27. Enable Monk Conversion

- ID: 27

- Purpose: Boolean: allow enemy monk conversions

- Default Values:

    - 0:  No (default)
    - $\geq$ 1:  Yes, after Atonement

## 28. Enable Building Conversion

- ID: 28

- Purpose: Boolean: allow enemy building conversions

- Default Values:

    - 0:  No (default)
    - 1:  Yes, after Redemption
    - $\geq$2:  Monks can convert buildings from range

## 29. Enable Siege Conversion

- ID: 29

- Purpose: Boolean: allow enemy siege conversions

- Default Values:

    - 0:  No (default)
    - 1:  Yes, after Redemption
    - $\geq$2:  Monks can convert siege from range

## 30. Unused Resource 030

- ID: 30

- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

## 31. Unused Resource 031

- ID: 31

- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

## 32. Bonus Population Cap

- ID: 32

- Purpose: Additional pop space to grant on top of maximum pop cap

- Note: 10 for goths

## 33. Effect Function Number

- ID: 33

- Purpose: Used to invoke functions in XS from data. When set to a non zero value `N`, it will automatically call a function named `EffectFunctionN` from the `Effects.xs` file.

## 34. Unused Resource 034

- ID: 34

- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

## 35. Unused Resource 035

- ID: 35

- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

## 36. Farm Food Amount

- ID: 36

- Purpose: Maximum farm food amount

- Default Values:

    - 175:  Default
    - 220:  Chinese

- Note: This is what horse collar etc. technologies modify

## 37. Civilian Population

- ID: 37

- Purpose: Current civilian population

## 38. Villager Population

- ID: 38

- Purpose: Current villager population

## 39. All Techs Achieved

- ID: 39

- Purpose: Boolean: If all available technologies have been researched

- Default Values:

    - 0:  No
    - 1:  Yes

## 40. Military Population

- ID: 40

- Purpose: Current military popupation

## 41. Conversions

- ID: 41

- Purpose: Number of units converted

## 42. Standing Wonders

- ID: 42

- Purpose: Number of standing wonders

## 43. Razings

- ID: 43

- Purpose: Number of buildings razed

## 44. Kill Ratio

- ID: 44

- Purpose: This is the number of units lost subtracted from the number of units killed in total

## 45. Survival to Finish

- ID: 45

- Purpose: Boolean: This is set to `0` under the same conditions which are required to defeat a player

- Default Values:

    - 0:  No
    - 1:  Yes

## 46. Tribute Inefficiency

- ID: 46

- Purpose: This is the fraction of tributes sent that are collected as tax

- Default Values:

    - 0.3:  Default
    - 0.2:  After Coinage
    - 0:  After Banking

## 47. Gold Mining Productivity

- ID: 47

- Purpose: Multiplier for gold mined by gold miners

- Default Values:

    - 1:  Default
    - 1.15:  Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%

## 48. Town Center Unavailable

- ID: 48

- Purpose: Boolean: allow building extra tcs

- Default Values:

    - 0:  No (Sudden Death)
    - 1:  Yes (Normal)

## 49. Gold Counter

- ID: 49

- Purpose: Total gold collected

## 50. Reveal Ally

- ID: 50

- Purpose: Boolean: show ally los for the source player

- Default Values:

    - 0:  No (default)
    - 1:  Yes, after Cartography or with a Portuguese ally

- Note: Once set to `1`, setting it back to `0` won't take away the LoS of allies

## 51. Unused Resource 051

- ID: 51

- Purpose: Unused

## 52. Monasteries

- ID: 52

- Purpose: Number of monasteries

## 53. Tribute Sent

- ID: 53

- Purpose: Total of all resources tributed to others. This does not count taxes paid on tributing

## 54. All Monuments Captured

- ID: 54

- Purpose: Boolean: all monuments on the map captured

- Default Values:

    - 0:  No
    - 1:  Yes

## 55. All Relics Captured

- ID: 55

- Purpose: Boolean: all relics on the map captured

- Default Values:

    - 0:  No
    - 1:  Yes

## 56. Ore Storage

- ID: 56

- Purpose: Unused

## 57. Kidnap Storage

- ID: 57

- Purpose: Number of units kidnapped

- Note: This is probably only used by mods, this usage may be incorrect

## 58. Dark Age Tech ID

- ID: 58

- Purpose: Always 104

- Note: Nothing happens when you change this

## 59. Unused Resource 059

- ID: 59

- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

## 60. Unused Resource 060

- ID: 60

- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

## 61. Unused Resource 061

- ID: 61

- Purpose: Unused

## 62. Building Housing Rate

- ID: 62

- Purpose: Unknown... What does this resource do?

## 63. Tax Gather Rate

- ID: 63

- Purpose: Unknown... What does this resource do?

## 64. Gather Accumulator

- ID: 64

- Purpose: Unknown... What does this resource do?

## 65. Salvage Decay Rate

- ID: 65

- Purpose: Unknown... What does this resource do?

## 66. Unused Resource 066

- ID: 66

- Purpose: This resource is unused but is known to sometimes have some values. Use with caution

## 67. Can Convert

- ID: 67

- Purpose: Boolean: monks can convert enemy units

- Default Values:

    - 0:  No
    - 1:  Yes (default)

## 68. Hit Points Killed

- ID: 68

- Purpose: Cumulative hp of all units killed

## 69. Farm Food Multiplier

- ID: 69

- Purpose: Multiplier for the amount of extra food granted by mill upgrades

- Default Values:

    - 1: No multiplier (default)

## 70. Source Market or Dock X Coordinate

- ID: 70

- Purpose: Controls the amount of gold that trade carts and trade cogs deposit, when the source market is changed

## 71. Source Market or Dock Y Coordinate

- ID: 71

- Purpose: Controls the amount of gold that trade carts and trade cogs deposit, when the source market is changed

## 72. Unused Resource 72

- ID: 72

- Purpose: Unused

## 73. Waypoint Sprite Graphic ID

- ID: 73

- Purpose: Per-civ waypoint flag graphic ID

## 74. Unused Resource 074

- ID: 74

- Purpose: Unused

## 75. Unused Resource 075

- ID: 75

- Purpose: Unused

## 76. Unused Resource 076

- ID: 76

- Purpose: Unused

## 77. Conversion Resistance

- ID: 77

- Purpose: Coefficient of conversion resistance

- Default Values:

    - 0:  Default

- Note: Probability of conversion every monk second is divided by this value for ALL source player units.

## 78. Trade Vig Rate

- ID: 78

- Purpose: Market exchange rate fraction for the source player

- Default Values:

    - 0.3:  Default
    - 0.15:  after Guilds
    - 0.05:  Saracens

## 79. Stone Mining Productivity

- ID: 79

- Purpose: Multiplier for stone mined by stone miners

- Default Values:

    - 1:  Default
    - 1.15:  Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%

## 80. Queued Units

- ID: 80

- Purpose: Amount of units in queue

- Note: Note that only the units waiting to be trained are considered in the queue so if an archery range has 3 archers being made, there is 1 archer that is being trained and 2 archers that are in queue

## 81. Training Count

- ID: 81

- Purpose: Amount of units being trained

- Note: Note that only the FIRST unit in each building is considered as being trained so if a town centre has 4 villagers being made, there is 1 archer that is being trained and 3 villagers that are in queue

## 82. Start with Unit 444 (PTWC)

- ID: 82

- Purpose: Boolean: started with PTWC

- Note: Setting this to 1 in an RMS allows for starting with PTWC. Manually changing this in the editor does nothing

## 83. Unused Resource 083

- ID: 83

- Purpose: Unused

## 84. Starting Villagers

- ID: 84

- Purpose: Number of starting villagers

- Default Values:

    - 3:  Default
    - 4:  Mayans
    - 6:  Chinese

- Note: Only works for RMS, changing this manually in the editor does nothing

## 85. Research Cost Modifier

- ID: 85

- Purpose: Multiply technology costs by this value

- Default Values:

    - 1:  Default
    - 0.9:  Chinese in feudal age
    - 0.85:  Chinese in castle age
    - 0.80:  Chinese in imperial age

## 86. Research Time Modifier

- ID: 86

- Purpose: Multiply technology research times by this value

## 87. Convert Boats

- ID: 87

- Purpose: Boolean: allow monks to convert boats

- Default Values:

    - 0:  No
    - 1:  Yes (default)

## 88. Fish Trap Food Amount

- ID: 88

- Purpose: Maximum fishtrap food amount

- Default Values:

    - 710:  Default
    - 2130:  Malay

## 89. Heal Rate Modifier

- ID: 89

- Purpose: Monk healing rate modifier

- Default Values:

    - 0:  The unit of measuremeant for this is unknown

## 90. Healing Range

- ID: 90

- Purpose: Monk heal range

- Default Values:

    - 4:  Tiles

## 91. Starting Food

- ID: 91

- Purpose: Starting food amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting food amount

## 92. Starting Wood

- ID: 92

- Purpose: Starting wood amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting wood amount

## 93. Starting Stone

- ID: 93

- Purpose: Starting stone amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting stone amount

## 94. Starting Gold

- ID: 94

- Purpose: Starting gold amount

- Note: Only works for RMS, changing this manually in the editor does nothing but its a way to check starting gold amount

## 95. Enable PTWC / Kidnap / Loot

- ID: 95

- Purpose: Enable town centre packing for the source player

- Default Values:

    - 0:  Default
    - 1:  Allows the TC to be packed and moved
    - $\geq$2:  No noticeable effect

- Note: Enabling kidnap/loot requires modding the units to have the kidnap/pillage action

## 96. No Dropsite Farmers

- ID: 96

- Purpose: Enable Khmer farmer bonus

- Default Values:

    - 0:  Default
    - 1:  Khmer. Farmers no longer need dropoff and steadily gain resources while farming

## 97. Dominant Sheep Control

- ID: 97

- Purpose: Boolean: force sheep conversion

- Default Values:

    - 0:  Default
    - $\geq$1:  Celts

- Note: If this is set to a non zero value, other players' sheep convert to you even if they have a unit in their LOS, unless this is also a non zero value for them. Celt sheep bonus

## 98. Building Cost Sum

- ID: 98

- Purpose: Total cost of all units and buildings owned

## 99. Tech Cost Sum

- ID: 99

- Purpose: Total cost of all researches researched

## 100. Relic Income Sum

- ID: 100

- Purpose: Total relic gold generated

## 101. Trade Income Sum

- ID: 101

- Purpose: Total trade gold generated

## 102. Naval Trade Wood

- ID: 102

- Purpose: Unknown

## 103. Unused Resource 103

- ID: 103

- Purpose: Unused

## 104. Unused Resource 104

- ID: 104

- Purpose: Unused

## 105. Unused Resource 105

- ID: 105

- Purpose: Unused

## 106. Unused Resource 106

- ID: 106

- Purpose: Unused

## 107. Unused Resource 107

- ID: 107

- Purpose: Unused

## 108. Unused Resource 108

- ID: 108

- Purpose: Unused

## 109. Unused Resource 109

- ID: 109

- Purpose: Unused

## 110. Unused Resource 110

- ID: 110

- Purpose: Unused

## 111. Unused Resource 111

- ID: 111

- Purpose: Unused

## 112. Unused Resource 112

- ID: 112

- Purpose: Unused

## 113. Unused Resource 113

- ID: 113

- Purpose: Unused

## 114. Unused Resource 114

- ID: 114

- Purpose: Unused

## 115. Unused Resource 115

- ID: 115

- Purpose: Unused

## 116. Unused Resource 116

- ID: 116

- Purpose: Unused

## 117. Unused Resource 117

- ID: 117

- Purpose: Unused

## 118. Unused Resource 118

- ID: 118

- Purpose: Unused

## 119. Unused Resource 119

- ID: 119

- Purpose: Unused

## 120. Unused Resource 120

- ID: 120

- Purpose: Unused

## 121. Unused Resource 121

- ID: 121

- Purpose: Unused

## 122. Unused Resource 122

- ID: 122

- Purpose: Unused

## 123. Unused Resource 123

- ID: 123

- Purpose: Unused

## 124. Unused Resource 124

- ID: 124

- Purpose: Unused

## 125. Unused Resource 125

- ID: 125

- Purpose: Unused

## 126. Unused Resource 126

- ID: 126

- Purpose: Unused

## 127. Unused Resource 127

- ID: 127

- Purpose: Unused

## 128. Unused Resource 128

- ID: 128

- Purpose: Unused

## 129. Unused Resource 129

- ID: 129

- Purpose: Unused

## 130. Unused Resource 130

- ID: 130

- Purpose: Unused

## 131. Unused Resource 131

- ID: 131

- Purpose: Unused

## 132. Unused Resource 132

- ID: 132

- Purpose: Unused

## 133. Unused Resource 133

- ID: 133

- Purpose: Unused

## 134. Standing Castles

- ID: 134

- Purpose: Number of standing castles

## 135. Hit Points Razed

- ID: 135

- Purpose: Total HP of all buildings destroyed

## 136. Unused Resource 136

- ID: 136

- Purpose: Unused

## 137. Unused Resource 137

- ID: 137

- Purpose: Unused

## 138. Unused Resource 138

- ID: 138

- Purpose: Unused

## 139. Unused Resource 139

- ID: 139

- Purpose: Unused

## 140. Unused Resource 140

- ID: 140

- Purpose: Unused

## 141. Unused Resource 141

- ID: 141

- Purpose: Unused

## 142. Unused Resource 142

- ID: 142

- Purpose: Unused

## 143. Unused Resource 143

- ID: 143

- Purpose: Unused

## 144. Unused Resource 144

- ID: 144

- Purpose: Unused

## 145. Unused Resource 145

- ID: 145

- Purpose: Unused

## 146. Unused Resource 146

- ID: 146

- Purpose: Unused

## 147. Unused Resource 147

- ID: 147

- Purpose: Unused

## 148. Unused Resource 148

- ID: 148

- Purpose: Unused

## 149. Unused Resource 149

- ID: 149

- Purpose: Unused

## 150. Unused Resource 150

- ID: 150

- Purpose: Unused

## 151. Unused Resource 151

- ID: 151

- Purpose: Unused

## 152. Value Killed by Others

- ID: 152

- Purpose: Total cost of all own units lost

## 153. Value Razed by Others

- ID: 153

- Purpose: Total cost of all own buildings lost

## 154. Killed by Others

- ID: 154

- Purpose: Number of own units killed by other players

## 155. Razed by Others

- ID: 155

- Purpose: Number of own buildings destroyed by other players

## 156. Unused Resource 156

- ID: 156

- Purpose: Unused

## 157. Unused Resource 157

- ID: 157

- Purpose: Unused

## 158. Unused Resource 158

- ID: 158

- Purpose: Unused

## 159. Unused Resource 159

- ID: 159

- Purpose: Unused

## 160. Unused Resource 160

- ID: 160

- Purpose: Unused

## 161. Unused Resource 161

- ID: 161

- Purpose: Unused

## 162. Unused Resource 162

- ID: 162

- Purpose: Unused

## 163. Unused Resource 163

- ID: 163

- Purpose: Unused

## 164. Value Current Units

- ID: 164

- Purpose: Total cost of all own alive units

## 165. Value Current Buildings

- ID: 165

- Purpose: Total cost of all own standing buildings

## 166. Food Total

- ID: 166

- Purpose: Total food collected

## 167. Wood Total

- ID: 167

- Purpose: Total wood collected

## 168. Stone Total

- ID: 168

- Purpose: Total stone collected

## 169. Gold Total

- ID: 169

- Purpose: Total gold collected

## 170. Total Value of Kills

- ID: 170

- Purpose: Total cost of all units killed

## 171. Total Tribute Received

- ID: 171

- Purpose: Total of all resources received in tribute

## 172. Total Value of Razings

- ID: 172

- Purpose: Total cost of all buildings destroyed

## 173. Total Castles Built

- ID: 173

- Purpose: Number of total castles built

## 174. Total Wonders Built

- ID: 174

- Purpose: Number of total wonders built

## 175. Tribute score

- ID: 175

- Purpose: Total amount of resources sent in tribute including taxes. 10% of this is counted towards the economy score

## 176. Convert Min Adjustment

- ID: 176

- Purpose: Additional monk seconds needed before a conversion is even possible

- Note: A great explanation of how this works [here](https://youtu.be/-qRUaOHpbwI?t=870 "Explanatory video by T-West") by T-West

## 177. Convert Max Adjustment

- ID: 177

- Purpose: Additional monk seconds needed before a conversion is forced

- Note: A great explanation of how this works [here](https://youtu.be/-qRUaOHpbwI?t=870 "Explanatory video by T-West") by T-West

## 178. Convert Resist Min Adjustment

- ID: 178

- Purpose: Additional monk seconds needed before conversion by enemy monks is even possible

- Note: A great explanation of how this works [here](https://youtu.be/-qRUaOHpbwI?t=830 "Explanatory video by T-West") by T-West

## 179. Convert Resist Max Adjustment

- ID: 179

- Purpose: Additional monk seconds needed before conversion by enemy monks is forced

- Note: A great explanation of how this works [here](https://youtu.be/-qRUaOHpbwI?t=830 "Explanatory video by T-West") by T-West.

## 180. Convert Building Min

- ID: 180

- Purpose: Minimum time required to convert a building

- Note: A great explanation of how this works [here](https://youtu.be/-qRUaOHpbwI?t=902 "Explanatory video by T-West") by T-West

## 181. Convert Building Max

- ID: 181

- Purpose: Maximum time required to convert a building

- Note: A great explanation for how this works [here](https://youtu.be/-qRUaOHpbwI?t=902 "Explanatory video by T-West") by T-West

## 182. Convert Building Chance

- ID: 182

- Purpose: Percent chance for monks to convert buildings

- Note: A great explanation for how this works [here](https://youtu.be/-qRUaOHpbwI?t=902 "Explanatory video by T-West") by T-West

## 183. Reveal Enemy

- ID: 183

- Purpose: Boolean: show enemy los for the source player

- Default Values:

    - 0:  No (default)
    - 1:  Yes, after Spies

- Note: Once set to `1`, setting it back to `0` won't take away LoS of enemies!

## 184. Value Wonders Castles

- ID: 184

- Purpose: Total cost of all wonders and castles constructed

## 185. Food Score

- ID: 185

- Purpose: Unknown... what does this resource do?

## 186. Wood Score

- ID: 186

- Purpose: Unknown... what does this resource do?

## 187. Stone Score

- ID: 187

- Purpose: Unknown... what does this resource do?

## 188. Gold Score

- ID: 188

- Purpose: Unknown... what does this resource do?

## 189. Chopping Productivity

- ID: 189

- Purpose: Multiplier for wood chopped by lumberjacks

- Default Values:

    - 1:  Default
    - 1.15:  Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%

## 190. Food Gathering Productivity

- ID: 190

- Purpose: Multiplier for food gathered from all sources

- Default Values:

    - 1:  Default
    - 1.15:  Mayans

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Mayans, This is compensated for by reducing villager work rate by 15%. The work rate for farmers is reduced by about 23.4%

## 191. Relic Gold Production Rate

- ID: 191

- Purpose: Relic gold generation rate in gold per minute

- Default Values:

    - 30:  Default. 30 gold per minute (0.5 gold per second)
    - 15:  After getting hit with Atheism

## 192. Converted Units Die

- ID: 192

- Purpose: Boolean: converted units die instead of switching over to the enemy

- Default Values:

    - 0:  No (default)
    - 1:  Yes, after Heresey

## 193. Theocracy

- ID: 193

- Purpose: Boolean: only one monk needs to regen faith after group conversion for the source player

- Default Values:

    - 0:  No (default)
    - 1:  Yes, after researching Theocracy

## 194. Unused Resource 194

- ID: 194

- Purpose: Unused

## 195. Construction Rate Modifier

- ID: 195

- Purpose: Builder work rate multiplier

- Default Values:

    - 0:  Default
    - 1.3:  Spanish

- Note: The actual work rate for builders is given by `construction_rate_mod * builder.default_work_rate`

## 196. Wonder Time Modifier

- ID: 196

- Purpose: Additional time required for wonder victories in one tenth of a year

- Default Values:

    - 0:  default
    - 1000:  (100 years) for all neutral/enemies of the Hun player, after researching atheism. The value of this resource of each player is added to determine the total extra time for wonder victories, i.e. it adds up if multiple hun players get the tech

- Note: Internally, wonder victory countdowns are measured in one tenths of an year, the fractional part is just not shown ingame

## 197. Spies Discount

- ID: 197

- Purpose: Boolean: Halves the cost of spies per villager, and caps it at 15k gold max instead of the usual 30k

- Default Values:

    - 0:  Default

## 198. Relic Time Modifier

- ID: 198

- Purpose: Additional time required for relic victories in one tenth of a year

- Default Values:

    - 0:  default
    - 1000:  (100 years) for all neutral/enemies of the Hun player, after researching atheism. The value of this resource of each player is added to determine the total extra time for relic victories, i.e. it adds up if multiple hun players get the tech

- Note: Internally, wonder victory countdowns are measured in one tenths of an year, the fractional part is just not shown ingame

## 199. Unused Resource 199

- ID: 199

- Purpose: Unused

## 200. Unused Resource 200

- ID: 200

- Purpose: Unused

## 201. Unused Resource 201

- ID: 201

- Purpose: Unused

## 202. Unused Resource 202

- ID: 202

- Purpose: Unused

## 203. Map Reveal

- ID: 203

- Purpose: Controls the map visibility for a player.

- Default Values:

    - 0:  Normal
    - 1:  Explored
    - 2:  All Visible

## 204. Unit Reveal

- ID: 204

- Purpose: Controls the visibility of other players' units for a player

- Note: Positive IDs will reveal a unit temporarily only when it is created, Negative IDs will reveal a unit permanently

## 205. Feitoria Food Productivity

- ID: 205

- Purpose: Feitoria food production rate multiplier

- Default Values:

    - 1:  Default

- Note: The amount of food obtained from owning `n` number of Feitorias is given by `n * feitoria_food_productivity * 1.6`

## 206. Feitoria Wood Productivity

- ID: 206

- Purpose: Feitoria wood production rate multiplier

- Default Values:

    - 1:  Default

- Note: The amount of wood obtained from owning `n` number of Feitorias is given by `n * feitoria_wood_productivity * 0.7`

## 207. Feitoria Stone Productivity

- ID: 207

- Purpose: Feitoria stone production rate multiplier

- Default Values:

    - 1:  Default

- Note: The amount of stone obtained from owning `n` number of Feitorias is given by `n * feitoria_stone_productivity * 0.3`

## 208. Feitoria Gold Productivity

- ID: 208

- Purpose: Feitoria gold production rate multiplier

- Default Values:

    - 1:  Default

- Note: The amount of gold obtained from owning `n` number of Feitorias is given by `n * feitoria_gold_productivity * 1`

## 209. Reveal Enemy Town Centers

- ID: 209

- Purpose: Boolean: reveal enemy town centre location for the source player

- Default Values:

    - 0:  Default
    - 5:  Vietnamese

- Note: The bonus works for all values $\geq$1, the choice of setting it to 5 for vietnamese seems arbitrary

## 210. Relics Visible on Map

- ID: 210

- Purpose: Boolean: reveal relics on map amount

- Default Values:

    - -1:  Default
    - 42:  Burmese

- Note: Burmese reveal relics on map bonus. Only works in RMS, manually changing this in the editor does not seem to have any effects

## 211. Elevation Higher Bonus

- ID: 211

- Purpose: The fraction for additional bonus damage dealt from higher elevation

- Default Values:

    - 0:  Default
    - 0.25:  Tatars

- Note: Damage that units on higher elevation deal to units on lower elevation is multiplied by `1.25 + elevation_bonus_higher`

## 212. Elevation Lower Bonus

- ID: 212

- Purpose: The fraction for additional bonus damage dealt from lower elevation

- Default Values:

    - 0:  Default

- Note: Damage that units on lower elevation deal to units on higher elevation is multiplied by `0.75 + elevation_bonus_lower`

## 213. Raiding Productivity

- ID: 213

- Purpose: Keshik gold generation rate per 100 seconds

- Default Values:

    - 0:  Default
    - 50:  (0.5 g/s) Tatars

- Note: Note that in practice, due to attack reload time and frame delay, Keshiks don't actually produce 0.5 g/s, but a slightly lower value

## 214. Mercenary Kipchak Count

- ID: 214

- Purpose: Total number of mercenary kipchak creatable

- Note: Researching Cuman Mercenaries gives 5 of this resource per castle. Making mercenary Kipchaks costs one unit of this resource. Each newly constructed castle gives +5

## 215. Bonus Forager Food

- ID: 215

- Purpose: Bonus forager food gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 25:  Mapuche

- Note: `EffectFunction29` must be called in order for this resource to work

## 216. Shepherd Productivity

- ID: 216

- Purpose: Amount of food collected from sheep multiplier

- Default Values:

    - 1:  Default
    - 1.57:  Tatars

- Note: Since this works by multiplying the amount of resources gathered by a villager, it has a side effect of increasing the gather rate. In the case of Tatars, This is compensated for by reducing villager work rate by 57%

## 217. Shared Line of Sight

- ID: 217

- Purpose: Unused

## 218. Early Town Center Limit

- ID: 218

- Purpose: This is the number of extra TCs a player is allowed to build IF TCs are enabled in feudal age

- Default Values:

    - 1:  Default
    - 2:  Cumans

- Note: Since generic civs don't get access to TCs in feudal, the 10k amount doesn't matter, but if you're trying to make a map where you want people to be able to make TCs in feudal, make sure to set this value to 10k for cumans!

## 219. Fishing Productivity

- ID: 219

- Purpose: Multiplier for food gathered by fishing ships

- Default Values:

    - 1:  Default

- Note: Since this works by multiplying the amount of resources gathered by a fishing ship, it has a side effect of increasing the gather rate

## 220. Enable Certain Hero Level Up (Unused Resource 220)

- ID: 220

- Purpose: Enables leveling up when killing units for `Richard the Lionheart`, `Sieur de Metz`, `Kushluk`, `Zawisza the Black`

- Default Values:

    - 0: Default

- Note: - This enabled `Loot` task which makes these heroes gain stats instead of resources.
- The editor name of the resource is incorrect

## 221. Monument Food Productivity

- ID: 221

- Purpose: Monument food trickle rate multiplier

- Default Values:

    - 1:  In KoTH games

- Note: The amount of resources obtained by owning a monument is `0.7925 * food_trickle_from_monument`

## 222. Monument Wood Productivity

- ID: 222

- Purpose: Monument wood trickle rate multiplier

- Default Values:

    - 1:  In KoTH games

- Note: The amount of resources obtained by owning a monument is `0.7925 * wood_trickle_from_monument`

## 223. Monument Stone Productivity

- ID: 223

- Purpose: Monument stone trickle rate multiplier

- Default Values:

    - 1:  In KoTH games

- Note: The amount of resources obtained by owning a monument is `0.7925 * stone_trickle_from_monument`

## 224. Monument Gold Productivity

- ID: 224

- Purpose: Monument gold trickle rate multiplier

- Default Values:

    - 1:  In KoTH games

- Note: The amount of resources obtained by owning a monument is `0.7925 * gold_trickle_from_monument`

## 225. Relic Food Production Rate

- ID: 225

- Purpose: Relic food production per minute

- Default Values:

    - 0:  Default
    - 30:  Burgundians
    - 15:  Burgundians after getting hit with Atheism

## 226. Villagers Killed by Gaia

- ID: 226

- Purpose: Total number of villagers lost to gaia

## 227. Villagers Killed by Animals

- ID: 227

- Purpose: Total number of villagers lost to wild animals

## 228. Villagers Killed by AI Player

- ID: 228

- Purpose: Total number of villagers lost to AIs

## 229. Villagers Killed by Human Player

- ID: 229

- Purpose: Total number of villagers lost to human players

## 230. Food Generation Rate

- ID: 230

- Purpose: Free food trickle rate (per minute)

## 231. Wood Generation Rate

- ID: 231

- Purpose: Free wood trickle rate (per minute)

## 232. Stone Generation Rate

- ID: 232

- Purpose: Free stone trickle rate (per minute)

## 233. Gold Generation Rate

- ID: 233

- Purpose: Free gold trickle rate (per minute)

## 234. Spawn Limit

- ID: 234

- Purpose: The limit to the number of spawning buildings that can spawn units from spawn command in a technology

- Note: This is usually overridden by techs

## 235. Flemish Militia Population

- ID: 235

- Purpose: Number of alive flemish militia

## 236. Farming Gold Productivity

- ID: 236

- Purpose: Farmer gold generation percent of main work rate

- Default Values:

    - 0:  Default
    - 2:  Burgundian Vineyards

- Note: `EffectFunction14` must be called for this resource to work. Only generates gold while collecting food from farms, and not when walking on them down

## 237. Folwark Collection Amount

- ID: 237

- Purpose: This is the amount of food collected from farms built around a folwark

- Default Values:

    - 0:  Default
    - 17.5:  Poles
    - 19.25:  Poles with Chinese Ally
    - 25:  Poles with Horse Collar
    - 27.5:  Poles with Horse Collar & Chinese Ally
    - 37.5:  Poles with Heavy Plow
    - 41.25:  Poles with Heavy Plow & Chinese Ally
    - 55:  Poles with Crop Rotation
    - 60.5:  Poles with Crop Rotation & Chinese Ally

## 238. Folwark Attribute Type

- ID: 238

- Purpose: This is the ID of the resource that is given when a farm is constructed around a folwark

- Default Values:

    - 0:  Poles
    - -1:  Default

## 239. Folwark Building Type

- ID: 239

- Purpose: This is the ID of the building that the Folwark needs to upgrade from for the farm collection ability to work

- Default Values:

    - 68:  (Mill) Poles
    - -1:  Default

## 240. Units Converted

- ID: 240

- Purpose: The amount of units lost to enemy conversions

## 241. Stone Mining Gold Productivity

- ID: 241

- Purpose: Bonus stone miner gold gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 33.33:  Poles

- Note: `EffectFunction13` must be called for this resource to work

## 242. Trade Workshop Food Productivity

- ID: 242

- Purpose: Trade Workshop food production rate multiplier

- Default Values:

    - 1:  Default

- Note: The amount of food obtained from owning `n` number of TWS (Unit 1647) is given by `n * tws_food_productivity * 2.25`

## 243. Trade Workshop Wood Productivity

- ID: 243

- Purpose: Trade Workshop wood production rate multiplier

- Default Values:

    - 1:  Default

- Note: The amount of wood obtained from owning `n` number of TWS (Unit 1647) is given by `n * tws_wood_productivity * 2.25`

## 244. Trade Workshop Stone Productivity

- ID: 244

- Purpose: Trade Workshop stone production rate multiplier

- Default Values:

    - 0:  Default

- Note: The amount of stone obtained from owning `n` number of TWS (Unit 1647) is given by `n * tws_stone_productivity * 2.25`

## 245. Trade Workshop Gold Productivity

- ID: 245

- Purpose: Trade Workshop gold production rate multiplier

- Default Values:

    - 1:  Default

- Note: The amount of gold obtained from owning `n` number of TWS (Unit 1647) is given by `n * tws_gold_productivity * 2.25`

## 246. Units Value Total

- ID: 246

- Purpose: Total cost of all units created so far

- Note: This does **not** decrease when the units die

## 247. Buildings Value Total

- ID: 247

- Purpose: Total cost of all buildings created so far

- Note: Increases when foundations are placed. This does **not** decrease if the foundation is deleted

## 248. Villagers Created Total

- ID: 248

- Purpose: Total number of villagers created so far

## 249. Villagers Idle Periods Total

- ID: 249

- Purpose: Amount of villagers that *entered* an idle state since game start

- Note:
    1. This only updates every 5 physical minutes.
    2. The number of villagers that *entered* an idle state since the last updated is added to this resource.
    3. Starting villager count is the initial value

## 250. Villagers Idle Seconds Total

- ID: 250

- Purpose: Amount of total seconds all villagers have been idle since game start

- Note:
    1. This only updates every 5 physical minutes.
    2. The idle time in seconds for all villagers since the last time this resource was updated is added  to this resource.
    3. A villager immediately adds its own idle time to this resource if it dies

## 251. Trade Food Percent

- ID: 251

- Purpose: Percentage of gold generated from trade that is also given as food

- Default Values:

    - 0:  Default
    - 10:  Bengalis

## 252. Trade Wood Percent

- ID: 252

- Purpose: Percentage of gold generated from trade that is also given as wood

- Default Values:

    - 0:  Default

## 253. Trade Stone Percent

- ID: 253

- Purpose: Percentage of gold generated from trade that is also given as stone

- Default Values:

    - 0:  Default

## 254. Livestock Food Productivity

- ID: 254

- Purpose: Garrisoned herdable food generation rate per 60 seconds

- Default Values:

    - 0:  Default
    - 3.5:  (0.0583 f/s per herdable) Gurjaras

## 255. Unused Resource 255

- ID: 255

- Purpose: Unused

## 256. Unused Resource 256

- ID: 256

- Purpose: Unused

## 257. Unused Resource 257

- ID: 257

- Purpose: Unused

## 258. Unused Resource 258

- ID: 258

- Purpose: Unused

## 259. Unused Resource 259

- ID: 259

- Purpose: Unused

## 260. Unused Resource 260

- ID: 260

- Purpose: Unused

## 261. Unused Resource 261

- ID: 261

- Purpose: Unused

## 262. Civilization Name Override

- ID: 262

- Purpose:

## 263. Starting Scout ID

- ID: 263

- Purpose: Unit ID for the starting scout. Can be set to any unit (even buildings)

- Default Values:

    - 448:  (Scout Cavalry) Default
    - 751:  (Eagle Scout) Aztecs, Incas and Mayans
    - 1755:  (Camel Scout) Gurjaras

## 264. Relic Wood Production Rate

- ID: 264

- Purpose: Relic wood production per minute

- Default Values:

    - 0:  Default

- Note: This is not affected by Atheism

## 265. Relic Stone Production Rate

- ID: 265

- Purpose: Relic stone production per minute

- Note: This is not affected by Atheism

## 266. Chopping Gold Productivity

- ID: 266

- Purpose: Lumberjack chopping gold gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 1.5:  Paper Money

- Note: `EffectFunction15` must be called for this resource to work. Only generates gold while collecting wood from trees, and not when cutting them down

## 267. Foraging Wood Productivity

- ID: 267

- Purpose: Bonus forager wood gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 33.33:  Portuguese

- Note: `EffectFunction12` must be called for this resource to work

## 268. Hunter Productivity

- ID: 268

- Purpose: Hunter hunting gold production rate per 100 seconds

## 269. Technology Reward Effect

- ID: 269

- Purpose: This is the ID of an additional effect which will fire when any technology is researched

## 270. Unit Repair Cost

- ID: 270

- Purpose: Percentage of cost required to repair siege units and ships

## 271. Building Repair Cost

- ID: 271

- Purpose: Percentage of cost required to repair buildings

## 272. Elevation Higher Damage

- ID: 272

- Purpose: Damage modifier for own units when attacked from higher elevation

- Note: This is applied after the calculations from [Elevation Higher Bonus](./#211-elevation-higher-bonus) and [Elevation Lower Bonus](./#212-elevation-lower-bonus)

## 273. Elevation Lower Damage

- ID: 273

- Purpose: Damage modifier for own units when attacked from lower elevation

- Note: This is applied after the calculations from [Elevation Higher Bonus](./#211-elevation-higher-bonus) and [Elevation Lower Bonus](./#212-elevation-lower-bonus)

## 274. Infantry Kill Reward

- ID: 274

- Purpose: This resource currently effectively enables/disables gold generation per second by infantry killing villagers, trade units and monks

- Default Values:

    - 0: All Civs
    - 1: Vikings after Chieftains

- Note: Technically, this resource is used as a multiplier for the resource generated by task 154 currently on infantry units. Task 154 can change which resource does this, and it is what really controls which resource is generated (Resource Out) and the rate of generation (Work Value 1) which is set to the different rates for different types of targets for infantry

## 275. Fyrd Discount Level

- ID: 275

- Purpose: The number of standing castles + TCs

- Note: This value only changes when a player is playing as the Saxons.

## 276. Bonus Gold Productivity

- ID: 276

- Purpose: Bonus gold miner gold gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 10:  Malians

- Note: `EffectFunction11` must be called in order for this resource to work

## 277. Red Cliffs Tactics Damage

- ID: 277

- Purpose: Multiplier for the amount of fire damage done by demolition ships

- Default Values:

    - 0: Before red cliffs tactics is researched
    - 1: After red cliffs tactics is researched

- Note: This implies that converted units that are affected by the tech won't do fire damage after being converted

## 278. Razing Bounty

- ID: 278

- Purpose: Currently Unused

## 279. Military Can Convert

- ID: 279

- Purpose: Military units with the conversion task can convert units if this is set to $>$ 0 for a player

## 280. Military Convert Range

- ID: 280

- Purpose: Adds to the conversion range of military units

## 281. Military Convert Chance

- ID: 281

- Purpose: Determines the conversion probability per monk second

## 282. Military Convert Recharge

- ID: 282

- Purpose: Determines the faith recharge rate after successful conversions

## 283. Spawn Inside

- ID: 283

- Purpose: Determines whenever spawned unit via `xsEffectAmount(cSpawnUnit,...)` or certain techs is spawned garrisoned or outside

- Default Values:

    - 0: All Civs
    - 1: Set briefly for the Armenians after their first Fortified Church is built to spawn the relic garrisoned.

- Note: This is usually overridden by techs

## 284. Cavalry Kill Reward

- ID: 284

- Purpose: This resource effectively sets the gold generation rate per second by cavalry fighting other military units

- Default Values:

    - 0: All Civs

- Note: Technically, this resource is used as a multiplier for the resource generated by task 154 currently on cavalry units. Task 154 can change which resource does this, and it is also what really controls which resource is generated (Resource Out) and the rate of generation (Work Value 1) which is just set to 1 for cavalry.

## 285. Shared Visibility

- ID: 285

- Purpose: This is a bitfield where the lowest 9 bits toggle sharing LoS with a specific player. The lowest bit represents gaia (player 0), and each higher bit represents the next player, so the bit for a given player is `1 << player` (`pow(2, player)`).

- Note: This does not change LoS for allies if the shared exploration setting in the lobby is enabled. Since this resource is a bitfield, when reading it with [xsPlayerAttribute](../../xs/functions/functions/#78-xsplayerattribute) or setting it with [xsSetPlayerAttribute](../../xs/functions/functions/#79-xssetplayerattribute), the value requires to be converted using [bitCastToInt](../../xs/functions/functions/#416-bitcasttoint) and [bitCastToFloat](../../xs/functions/functions/#415-bitcasttofloat) respectively, so that the individual bits can be read and set correctly.

## 286. Shared Exploration

- ID: 286

- Purpose: This is a bitfield where the lowest 9 bits toggle sharing map exploration with a specific player. The lowest bit represents gaia (player 0), and each higher bit represents the next player, so the bit for a given player is `1 << player` (`pow(2, player)`).

- Note: This does not change exploration for allies if the shared exploration setting in the lobby is enabled. Since this resource is a bitfield, when reading it with [xsPlayerAttribute](../../xs/functions/functions/#78-xsplayerattribute) or setting it with [xsSetPlayerAttribute](../../xs/functions/functions/#79-xssetplayerattribute), the value requires to be converted using [bitCastToInt](../../xs/functions/functions/#416-bitcasttoint) and [bitCastToFloat](../../xs/functions/functions/#415-bitcasttofloat) respectively, so that the individual bits can be read and set correctly.

## 287. Military Food Productivity

- ID: 287

- Purpose: The amount of food generated by soldiers per 100 seconds

## 288. Pasture Food Amount

- ID: 288

- Purpose: Determines the amount of food pastures provide

## 289. Pasture Animal Count

- ID: 289

- Purpose: Determines the amount of animals on a pasture.

## 290. Pasture Herder Count

- ID: 290

- Purpose: Determines the maximum amount of villagers that can work at once on a pasture

## 291. Razing Pillage

- ID: 291

- Purpose: The percent * 10 of the cost that should be looted when destroying buildings.

- Default Values:

    - 0:  Default
    - 250:  Danes

- Note: `EffectFunction36` must be called for all players in the game for this resource to work.

## 292. Animal Decay Prevention

- ID: 292

- Purpose: Prevents animal corpses from losing food when being gathered by a villager

## 293. Herder Food Productivity

- ID: 293

- Purpose: Percent extra food generated by herders and shepherds

## 294. Shepherd Food Productivity

- ID: 294

- Purpose: Percent extra food generated by herders and shepherds

## 295. Unit Refund

- ID: 295

- Purpose: Fraction of the cost to refund for lost units for the player

- Default Values:

    - 0:  Default
    - 0.15:  Tupi

- Note: `EffectFunction27` must be called for this resource to work.

## 296. Forager Productivity

- ID: 296

- Purpose: Multiplier for food collected by foragers

- Default Values:

    - 1:  Default

## 297. Varangian Gold Generation

- ID: 297

- Purpose: Varangian Guard gold generation multiplier

- Default Values:

    - 1:  Default
    - 1.33:  Varangians

## 298. Butcher Gold Productivity

- ID: 298

- Purpose: Varangians Shepherd/Hunter/Fisher/Fishing Ship additional gold gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 10.01:  Varangians

- Note: `EffectFunction34` must be called for this resource to work.

## 299. Bonus Food Productivity

- ID: 299

- Purpose: All food gatherers additional food gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 5.01:  Danes

- Note: `EffectFunction35` must be called for this resource to work.

## 300. Killed Gaia

- ID: 300

- Purpose: Number of gaia units killed

## 301. Killed P1

- ID: 301

- Purpose: Number of player 1 units killed

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 302. Killed P2

- ID: 302

- Purpose: Number of player 2 units killed

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 303. Killed P3

- ID: 303

- Purpose: Number of player 3 units killed

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 304. Killed P4

- ID: 304

- Purpose: Number of player 4 units killed

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 305. Killed P5

- ID: 305

- Purpose: Number of player 5 units killed

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 306. Killed P6

- ID: 306

- Purpose: Number of player 6 units killed

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 307. Killed P7

- ID: 307

- Purpose: Number of player 7 units killed

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 308. Killed P8

- ID: 308

- Purpose: Number of player 8 units killed

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 309. Unused Resource 309

- ID: 309

- Purpose: Unused

## 310. Unused Resource 310

- ID: 310

- Purpose: Unused

## 311. Unused Resource 311

- ID: 311

- Purpose: Unused

## 312. Unused Resource 312

- ID: 312

- Purpose: Unused

## 313. Unused Resource 313

- ID: 313

- Purpose: Unused

## 314. Unused Resource 314

- ID: 314

- Purpose: Unused

## 315. Unused Resource 315

- ID: 315

- Purpose: Unused

## 316. Unused Resource 316

- ID: 316

- Purpose: Unused

## 317. Unused Resource 317

- ID: 317

- Purpose: Unused

## 318. Unused Resource 318

- ID: 318

- Purpose: Unused

## 319. Unused Resource 319

- ID: 319

- Purpose: Unused

## 320. Unused Resource 320

- ID: 320

- Purpose: Unused

## 321. Unused Resource 321

- ID: 321

- Purpose: Unused

## 322. Unused Resource 322

- ID: 322

- Purpose: Unused

## 323. Unused Resource 323

- ID: 323

- Purpose: Unused

## 324. Unused Resource 324

- ID: 324

- Purpose: Unused

## 325. Kills by Gaia

- ID: 325

- Purpose: Number of own units killed by Gaia

## 326. Kills by P1

- ID: 326

- Purpose: Number of own units killed by player 1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 327. Kills by P2

- ID: 327

- Purpose: Number of own units killed by player 2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 328. Kills by P3

- ID: 328

- Purpose: Number of own units killed by player 3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 329. Kills by P4

- ID: 329

- Purpose: Number of own units killed by player 4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 330. Kills by P5

- ID: 330

- Purpose: Number of own units killed by player 5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 331. Kills by P6

- ID: 331

- Purpose: Number of own units killed by player 6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 332. Kills by P7

- ID: 332

- Purpose: Number of own units killed by player 7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 333. Kills by P8

- ID: 333

- Purpose: Number of own units killed by player 8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 334. Unused Resource 334

- ID: 334

- Purpose: Unused

## 335. Unused Resource 335

- ID: 335

- Purpose: Unused

## 336. Unused Resource 336

- ID: 336

- Purpose: Unused

## 337. Unused Resource 337

- ID: 337

- Purpose: Unused

## 338. Unused Resource 338

- ID: 338

- Purpose: Unused

## 339. Unused Resource 339

- ID: 339

- Purpose: Unused

## 340. Unused Resource 340

- ID: 340

- Purpose: Unused

## 341. Unused Resource 341

- ID: 341

- Purpose: Unused

## 342. Unused Resource 342

- ID: 342

- Purpose: Unused

## 343. Unused Resource 343

- ID: 343

- Purpose: Unused

## 344. Unused Resource 344

- ID: 344

- Purpose: Unused

## 345. Unused Resource 345

- ID: 345

- Purpose: Unused

## 346. Unused Resource 346

- ID: 346

- Purpose: Unused

## 347. Unused Resource 347

- ID: 347

- Purpose: Unused

## 348. Unused Resource 348

- ID: 348

- Purpose: Unused

## 349. Unused Resource 349

- ID: 349

- Purpose: Unused

## 350. Gaia Razings

- ID: 350

- Purpose: Number of buildings destroyed of Gaia

## 351. P1 Razings

- ID: 351

- Purpose: Number of buildings destroyed of player 1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 352. P2 Razings

- ID: 352

- Purpose: Number of buildings destroyed of player 2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 353. P3 Razings

- ID: 353

- Purpose: Number of buildings destroyed of player 3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 354. P4 Razings

- ID: 354

- Purpose: Number of buildings destroyed of player 4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 355. P5 Razings

- ID: 355

- Purpose: Number of buildings destroyed of player 5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 356. P6 Razings

- ID: 356

- Purpose: Number of buildings destroyed of player 6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 357. P7 Razings

- ID: 357

- Purpose: Number of buildings destroyed of player 7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 358. P8 Razings

- ID: 358

- Purpose: Number of buildings destroyed of player 8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 359. Unused Resource 359

- ID: 359

- Purpose: Unused

## 360. Unused Resource 360

- ID: 360

- Purpose: Unused

## 361. Unused Resource 361

- ID: 361

- Purpose: Unused

## 362. Unused Resource 362

- ID: 362

- Purpose: Unused

## 363. Unused Resource 363

- ID: 363

- Purpose: Unused

## 364. Unused Resource 364

- ID: 364

- Purpose: Unused

## 365. Unused Resource 365

- ID: 365

- Purpose: Unused

## 366. Unused Resource 366

- ID: 366

- Purpose: Unused

## 367. Unused Resource 367

- ID: 367

- Purpose: Unused

## 368. Unused Resource 368

- ID: 368

- Purpose: Unused

## 369. Unused Resource 369

- ID: 369

- Purpose: Unused

## 370. Unused Resource 370

- ID: 370

- Purpose: Unused

## 371. Unused Resource 371

- ID: 371

- Purpose: Unused

## 372. Unused Resource 372

- ID: 372

- Purpose: Unused

## 373. Unused Resource 373

- ID: 373

- Purpose: Unused

## 374. Unused Resource 374

- ID: 374

- Purpose: Unused

## 375. Razings by Gaia

- ID: 375

- Purpose: Number of own buildings destroyed by Gaia

## 376. Razings by P1

- ID: 376

- Purpose: Number of own buildings destroyed by player 1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 377. Razings by P2

- ID: 377

- Purpose: Number of own buildings destroyed by player 2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 378. Razings by P3

- ID: 378

- Purpose: Number of own buildings destroyed by player 3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 379. Razings by P4

- ID: 379

- Purpose: Number of own buildings destroyed by player 4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 380. Razings by P5

- ID: 380

- Purpose: Number of own buildings destroyed by player 5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 381. Razings by P6

- ID: 381

- Purpose: Number of own buildings destroyed by player 6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 382. Razings by P7

- ID: 382

- Purpose: Number of own buildings destroyed by player 7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 383. Razings by P8

- ID: 383

- Purpose: Number of own buildings destroyed by player 8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 384. Unused Resource 384

- ID: 384

- Purpose: Unused

## 385. Unused Resource 385

- ID: 385

- Purpose: Unused

## 386. Unused Resource 386

- ID: 386

- Purpose: Unused

## 387. Unused Resource 387

- ID: 387

- Purpose: Unused

## 388. Unused Resource 388

- ID: 388

- Purpose: Unused

## 389. Unused Resource 389

- ID: 389

- Purpose: Unused

## 390. Unused Resource 390

- ID: 390

- Purpose: Unused

## 391. Unused Resource 391

- ID: 391

- Purpose: Unused

## 392. Unused Resource 392

- ID: 392

- Purpose: Unused

## 393. Unused Resource 393

- ID: 393

- Purpose: Unused

## 394. Unused Resource 394

- ID: 394

- Purpose: Unused

## 395. Unused Resource 395

- ID: 395

- Purpose: Unused

## 396. Unused Resource 396

- ID: 396

- Purpose: Unused

## 397. Unused Resource 397

- ID: 397

- Purpose: Unused

## 398. Unused Resource 398

- ID: 398

- Purpose: Unused

## 399. Unused Resource 399

- ID: 399

- Purpose: Unused

## 400. Gaia Kill Value

- ID: 400

- Purpose: Total cost of all units killed of Gaia

## 401. P1 Kill Value

- ID: 401

- Purpose: Total cost of all units killed of player 1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 402. P2 Kill Value

- ID: 402

- Purpose: Total cost of all units killed of player 2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 403. P3 Kill Value

- ID: 403

- Purpose: Total cost of all units killed of player 3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 404. P4 Kill Value

- ID: 404

- Purpose: Total cost of all units killed of player 4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 405. P5 Kill Value

- ID: 405

- Purpose: Total cost of all units killed of player 5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 406. P6 Kill Value

- ID: 406

- Purpose: Total cost of all units killed of player 6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 407. P7 Kill Value

- ID: 407

- Purpose: Total cost of all units killed of player 7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 408. P8 Kill Value

- ID: 408

- Purpose: Total cost of all units killed of player 8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 409. Unused Resource 409

- ID: 409

- Purpose: Unused

## 410. Unused Resource 410

- ID: 410

- Purpose: Unused

## 411. Unused Resource 411

- ID: 411

- Purpose: Unused

## 412. Unused Resource 412

- ID: 412

- Purpose: Unused

## 413. Unused Resource 413

- ID: 413

- Purpose: Unused

## 414. Unused Resource 414

- ID: 414

- Purpose: Unused

## 415. Unused Resource 415

- ID: 415

- Purpose: Unused

## 416. Unused Resource 416

- ID: 416

- Purpose: Unused

## 417. Unused Resource 417

- ID: 417

- Purpose: Unused

## 418. Unused Resource 418

- ID: 418

- Purpose: Unused

## 419. Unused Resource 419

- ID: 419

- Purpose: Unused

## 420. Unused Resource 420

- ID: 420

- Purpose: Unused

## 421. Unused Resource 421

- ID: 421

- Purpose: Unused

## 422. Unused Resource 422

- ID: 422

- Purpose: Unused

## 423. Unused Resource 423

- ID: 423

- Purpose: Unused

## 424. Unused Resource 424

- ID: 424

- Purpose: Unused

## 425. Gaia Razing Value

- ID: 425

- Purpose: Total cost of all buildings destroyed of Gaia

## 426. P1 Razing Value

- ID: 426

- Purpose: Total cost of all buildings destroyed of player 1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 427. P2 Razing Value

- ID: 427

- Purpose: Total cost of all buildings destroyed of player 2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 428. P3 Razing Value

- ID: 428

- Purpose: Total cost of all buildings destroyed of player 3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 429. P4 Razing Value

- ID: 429

- Purpose: Total cost of all buildings destroyed of player 4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 430. P5 Razing Value

- ID: 430

- Purpose: Total cost of all buildings destroyed of player 5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 431. P6 Razing Value

- ID: 431

- Purpose: Total cost of all buildings destroyed of player 6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 432. P7 Razing Value

- ID: 432

- Purpose: Total cost of all buildings destroyed of player 7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 433. P8 Razing Value

- ID: 433

- Purpose: Total cost of all buildings destroyed of player 8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 434. Unused Resource 434

- ID: 434

- Purpose: Unused

## 435. Unused Resource 435

- ID: 435

- Purpose: Unused

## 436. Unused Resource 436

- ID: 436

- Purpose: Unused

## 437. Unused Resource 437

- ID: 437

- Purpose: Unused

## 438. Unused Resource 438

- ID: 438

- Purpose: Unused

## 439. Unused Resource 439

- ID: 439

- Purpose: Unused

## 440. Unused Resource 440

- ID: 440

- Purpose: Unused

## 441. Unused Resource 441

- ID: 441

- Purpose: Unused

## 442. Unused Resource 442

- ID: 442

- Purpose: Unused

## 443. Unused Resource 443

- ID: 443

- Purpose: Unused

## 444. Unused Resource 444

- ID: 444

- Purpose: Unused

## 445. Unused Resource 445

- ID: 445

- Purpose: Unused

## 446. Unused Resource 446

- ID: 446

- Purpose: Unused

## 447. Unused Resource 447

- ID: 447

- Purpose: Unused

## 448. Unused Resource 448

- ID: 448

- Purpose: Unused

## 449. Unused Resource 449

- ID: 449

- Purpose: Unused

## 450. Gaia Tribute

- ID: 450

- Purpose: Amount of resources tributed to Gaia

## 451. P1 Tribute

- ID: 451

- Purpose: Amount of resources tributed to player 1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 452. P2 Tribute

- ID: 452

- Purpose: Amount of resources tributed to player 2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 453. P3 Tribute

- ID: 453

- Purpose: Amount of resources tributed to player 3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 454. P4 Tribute

- ID: 454

- Purpose: Amount of resources tributed to player 4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 455. P5 Tribute

- ID: 455

- Purpose: Amount of resources tributed to player 5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 456. P6 Tribute

- ID: 456

- Purpose: Amount of resources tributed to player 6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 457. P7 Tribute

- ID: 457

- Purpose: Amount of resources tributed to player 7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 458. P8 Tribute

- ID: 458

- Purpose: Amount of resources tributed to player 8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 459. Unused Resource 459

- ID: 459

- Purpose: Unused

## 460. Unused Resource 460

- ID: 460

- Purpose: Unused

## 461. Unused Resource 461

- ID: 461

- Purpose: Unused

## 462. Unused Resource 462

- ID: 462

- Purpose: Unused

## 463. Unused Resource 463

- ID: 463

- Purpose: Unused

## 464. Unused Resource 464

- ID: 464

- Purpose: Unused

## 465. Unused Resource 465

- ID: 465

- Purpose: Unused

## 466. Unused Resource 466

- ID: 466

- Purpose: Unused

## 467. Unused Resource 467

- ID: 467

- Purpose: Unused

## 468. Unused Resource 468

- ID: 468

- Purpose: Unused

## 469. Unused Resource 469

- ID: 469

- Purpose: Unused

## 470. Unused Resource 470

- ID: 470

- Purpose: Unused

## 471. Unused Resource 471

- ID: 471

- Purpose: Unused

## 472. Unused Resource 472

- ID: 472

- Purpose: Unused

## 473. Unused Resource 473

- ID: 473

- Purpose: Unused

## 474. Unused Resource 474

- ID: 474

- Purpose: Unused

## 475. Tribute from Gaia

- ID: 475

- Purpose: Tribute received from Gaia

## 476. Tribute from P1

- ID: 476

- Purpose: Tribute received from player 1

- Note: This refers to lobby/slot/world player 1, not editor/scenario player 1

## 477. Tribute from P2

- ID: 477

- Purpose: Tribute received from player 2

- Note: This refers to lobby/slot/world player 2, not editor/scenario player 2

## 478. Tribute from P3

- ID: 478

- Purpose: Tribute received from player 3

- Note: This refers to lobby/slot/world player 3, not editor/scenario player 3

## 479. Tribute from P4

- ID: 479

- Purpose: Tribute received from player 4

- Note: This refers to lobby/slot/world player 4, not editor/scenario player 4

## 480. Tribute from P5

- ID: 480

- Purpose: Tribute received from player 5

- Note: This refers to lobby/slot/world player 5, not editor/scenario player 5

## 481. Tribute from P6

- ID: 481

- Purpose: Tribute received from player 6

- Note: This refers to lobby/slot/world player 6, not editor/scenario player 6

## 482. Tribute from P7

- ID: 482

- Purpose: Tribute received from player 7

- Note: This refers to lobby/slot/world player 7, not editor/scenario player 7

## 483. Tribute from P8

- ID: 483

- Purpose: Tribute received from player 8

- Note: This refers to lobby/slot/world player 8, not editor/scenario player 8

## 484. Unused Resource 484

- ID: 484

- Purpose: Unused

## 485. Unused Resource 485

- ID: 485

- Purpose: Unused

## 486. Unused Resource 486

- ID: 486

- Purpose: Unused

## 487. Unused Resource 487

- ID: 487

- Purpose: Unused

## 488. Unused Resource 488

- ID: 488

- Purpose: Unused

## 489. Unused Resource 489

- ID: 489

- Purpose: Unused

## 490. Unused Resource 490

- ID: 490

- Purpose: Unused

## 491. Unused Resource 491

- ID: 491

- Purpose: Unused

## 492. Unused Resource 492

- ID: 492

- Purpose: Unused

## 493. Unused Resource 493

- ID: 493

- Purpose: Unused

## 494. Unused Resource 494

- ID: 494

- Purpose: Unused

## 495. Unused Resource 495

- ID: 495

- Purpose: Unused

## 496. Unused Resource 496

- ID: 496

- Purpose: Unused

## 497. Unused Resource 497

- ID: 497

- Purpose: Unused

## 498. Unused Resource 498

- ID: 498

- Purpose: Unused

## 499. Unused Resource 499

- ID: 499

- Purpose: Unused

## 500. Unused Resource 500

- ID: 500

- Purpose: Unused

## 501. Polemarch Build Limit

- ID: 501

- Purpose: Hidden resource that is part of the cost of Polemarch. Incremented when the Polemarch dies, decremented when a Polemarch is trained. Increment this value to allow training of more Polemarchs

- Default Values:

    - 0: Default

## 502. Athenian Chopping Food Productivity

- ID: 502

- Purpose: Chopping food gathering percent of main work rate

- Default Values:

    - 0:  Default
    - 4:  Athenians
    - 7:  Shu

- Note: `EffectFunction16` must be called for this resource to work. While the name only contains Athenians, this resource is also used for Shu.

## 503. Wood Trade Ratio

- ID: 503

- Purpose: Amount of trade will be returned as wood instead of gold.

- Default Values:

    - 0:  Default
    - 0.25:  Achaemenids, Athenians and Spartans.

- Note: Changed in the Battle of Greece civs Port by a toggle to 0.25, 0.5, and 0.75 or by researching equivalent tech in the editor. Setting it to 0.5 will return half the amount in gold and half in wood. Works for trade cogs only. Setting it to a value $\geq$ 1 will make it so no trade resources are returned.

## 504. Unused Resource 504

- ID: 504

- Purpose: Unused but civs start with 1 at the start of the game. Also unused `Spanish team bonus` effect multiplies its value by 0.8

- Default Values:

    - 1: At the start of the game. Does not seem to do anything

## 505. Unused Resource 505

- ID: 505

- Purpose: Unused, but Achaemenids, Athenians and Spartans have it set to 1

- Default Values:

    - 0:  Default
    - 1:  Achaemenids, Athenians and Spartans

## 506. Achaemenid Town Center Local Upgrade

- ID: 506

- Purpose: Used as a local resource in Town Centers to know which of them have the Achamenids Town Center upgrade researched

- Default Values:

    - 0:  Default
    - 1:  Achaemenids, Athenians and Spartans

- Note: Achamenids Town Center Local Upgrade resource is changed when its tech is researched. As a side effect its global player value will be decremented every time a Town Center is destroyed.

## 507. Unused Resource 507

- ID: 507

- Purpose: Unused, but `Athenians Static Bonuses` effect sets it to 1

- Default Values:

    - 0:  Default
    - 1:  Athenians

- Note: Athenians start with it set to 1 by initial Economic Policy.

## 508. Fortified Outpost Local Upgrade

- ID: 508

- Purpose: Used as a local resource in `Outposts`

- Note: Fortified Outpost Local Upgrade resource is changed when its tech is researched. As a side effect its global player value will be decremented every time an Outpost is destroyed.

## 509. Mercenary Hoplite Productivity

- ID: 509

- Purpose: It is named in the editor but seems to no longer affect `Mercenary Hoplite` and therefore unused

## 510. Odomantian Raiders Productivity

- ID: 510

- Purpose: Modifies how much gold units gain affected by `Odomantian Raiders` tech

- Default Values:

    - 0: Default
    - 1: Spartans or after Odomantian Raiders is researched

## 511. Dii Plunderers Productivity

- ID: 511

- Purpose: Modifies how much resources units gain affected by `Dii Plunderers` tech

- Default Values:

    - 0: Default
    - 1: After Dii Plunderers is researched

## 512. Stone Mining Food Productivity

- ID: 512

- Purpose: Stone mining food generation rate

- Default Values:

    - 0: Default
    - 1: Puru

## 513. Emplacement Local Upgrade

- ID: 513

- Purpose: Used as a local cost to upgrade `Fort` to an emplacement

## 514. Helepolis Limit

- ID: 514

- Purpose: Limit the amount of `Helepolis` that can be built. Only works if `Helepolis` are built as buildings

## 515. Scythian Horse Archer Productivity

- ID: 515

- Purpose: Modifies how much gold `Scythian Horse Archer` and `Elite Scythian Horse Archer` gain when killing units

- Default Values:

    - 1: Default
    - 0: Shu, Wu, Wei, Jurchens, Khitans

## 516. Unused Resource 516

- ID: 516

- Purpose: Unused

## 517. Unused Resource 517

- ID: 517

- Purpose: Unused

## 518. Unused Resource 518

- ID: 518

- Purpose: Unused

## 519. Unused Resource 519

- ID: 519

- Purpose: Unused

## 520. Lysanders Raider Productivity

- ID: 520

- Purpose: Modifies how much gold `Lysanders Raider` gains when killing units

- Default Values:

    - 1:  Default

## 521. Peloponnesian League Productivity

- ID: 521

- Purpose: Castle gold production rate multiplier

- Default Values:

    - 0:  Default
    - 1:  After Peloponnesian League researched

- Note: The amount of gold obtained from owning `n` number of Castles is given by `n * castle_gold_productivity * 0.33333`.

## 522. Base Hoplite Aura Enabled

- ID: 522

- Purpose: Turns on base `Hoplite` aura

- Default Values:

    - 1: Default
    - 0: Macedonians, Thracians, Puru or after Agoge is researched

## 523. Agoge Hoplite Aura Enabled

- ID: 523

- Purpose: Turns on aura gained via `Agoge` tech for `Hoplites`

- Default Values:

    - 1: After Agoge is researched
    - 0: Default

## 524. Xyphos Hoplite Aura Enabled

- ID: 524

- Purpose: Turns on aura gained via `Xyphos` tech for `Hoplites`

- Default Values:

    - 1: After Xyphos is researched
    - 0: Default

## 525. Base Strategos Aura Enabled

- ID: 525

- Purpose: Turns on base `Strategos` aura

- Default Values:

    - 1: Default
    - 0: Macedonians, Thracians, Puru or after Taxiarchs is researched

## 526. Taxiarchs Strategos Aura Enabled

- ID: 526

- Purpose: Turns on aura gained via `Taxiarchs` tech for `Strategos`

- Default Values:

    - 1: After Taxiarchs is researched
    - 0: Default

## 527. Hippeus Aura No Tech

- ID: 527

- Purpose: Turns on base `Hippeus` aura

- Default Values:

    - 1: Default
    - 0: Macedonians, Thracians, Puru or after Morai is researched

## 528. Hippeus Aura With Techs

- ID: 528

- Purpose: Turns on aura gained via `Morai` tech for `Hippeus`

- Default Values:

    - 1: After Morai is researched
    - 0: Default

## 529. Unused Resource 529

- ID: 529

- Purpose: Unused

## 530. Unused Resource 530

- ID: 530

- Purpose: Unused

## 531. Scenario Resource 01

- ID: 531

- Purpose: Unused

## 532. Scenario Resource 02

- ID: 532

- Purpose: Unused

## 533. Scenario Resource 03

- ID: 533

- Purpose: Unused

## 534. Scenario Resource 04

- ID: 534

- Purpose: Unused

## 535. Scenario Resource 05

- ID: 535

- Purpose: Unused

## 536. Scenario Resource 06

- ID: 536

- Purpose: Unused

## 537. Scenario Resource 07

- ID: 537

- Purpose: Unused

## 538. Scenario Resource 08

- ID: 538

- Purpose: Unused

## 539. Scenario Resource 09

- ID: 539

- Purpose: Unused

## 540. Scenario Resource 10

- ID: 540

- Purpose: Unused

## 541. Scenario Resource 11

- ID: 541

- Purpose: Unused

## 542. Scenario Resource 12

- ID: 542

- Purpose: Unused

## 543. Scenario Resource 13

- ID: 543

- Purpose: Unused

## 544. Scenario Resource 14

- ID: 544

- Purpose: Unused

## 545. Scenario Resource 15

- ID: 545

- Purpose: Unused

## 546. Scenario Resource 16

- ID: 546

- Purpose: Unused

## 547. Scenario Resource 17

- ID: 547

- Purpose: Unused

## 548. Unused Resource 548

- ID: 548

- Purpose: Unused

## 549. Unused Resource 549

- ID: 549

- Purpose: Unused

## 550. Camel Raider Productivity

- ID: 550

- Purpose: Modifies how much gold `Lysander's Raider` and `Camel Raider` gain when killing units

- Default Values:

    - 1:  Default

## 551. Tyranny Productivity

- ID: 551

- Purpose: Gain gold per unit killed

- Default Values:

    - 0:  Default
    - 1:  After Military Policy activated

- Note: The amount of gold obtained from killing number of units `u` is `u * unit_loot_productivity * 3`. Unlike resources 520 and 550 works on most units. Look at A.G.E. for units with 154 loot class task.

## 552. Unused Resource 552

- ID: 552

- Purpose: Unused

## 553. Unused Resource 553

- ID: 553

- Purpose: Unused

## 554. Unused Resource 554

- ID: 554

- Purpose: Unused

## 555. Unused Resource 555

- ID: 555

- Purpose: Unused

## 556. Unused Resource 556

- ID: 556

- Purpose: Unused

## 557. Unused Resource 557

- ID: 557

- Purpose: Unused

## 558. Unused Resource 558

- ID: 558

- Purpose: Unused

## 559. Unused Resource 559

- ID: 559

- Purpose: Unused

## 560. Ends of the World Productivity

- ID: 560

- Purpose: Turns on aura gained via `Ends of the World` tech for `Fortified Outpost`

## 561. Pattiyodha Longbowman Default

- ID: 561

- Purpose: Turns on base `Pattiyodha Longbowman` aura

- Default Values:

    - 1: Default
    - 0: Macedonians, Thracians, Puru or after Leaf-Headed Shafts is researched

## 562. Pattiyodha Longbowman Upgraded

- ID: 562

- Purpose: Turns on aura gained via `Leaf-Headed Shafts` tech for `Pattiyodha Longbowman`

- Default Values:

    - 1: After Leaf-Headed Shafts is researched
    - 0: Default

## 563. Shepherd Gold Productivity

- ID: 563

- Purpose: Sheep herding and hunting gold generation rate

- Default Values:

    - 0: Default
    - 1: Thracians

## 564. Unused Resource 564

- ID: 564

- Purpose: Unused

## 565. Unused Resource 565

- ID: 565

- Purpose: Unused

## 566. Unused Resource 566

- ID: 566

- Purpose: Unused

## 567. Unused Resource 567

- ID: 567

- Purpose: Unused

## 568. Unused Resource 568

- ID: 568

- Purpose: Unused

## 569. Unused Resource 569

- ID: 569

- Purpose: Unused

## 570. Unused Resource 570

- ID: 570

- Purpose: Unused

## 571. Unused Resource 571

- ID: 571

- Purpose: Unused

## 572. Unused Resource 572

- ID: 572

- Purpose: Unused

## 573. Unused Resource 573

- ID: 573

- Purpose: Unused

## 574. Unused Resource 574

- ID: 574

- Purpose: Unused

## 575. Unused Resource 575

- ID: 575

- Purpose: Unused

## 576. Unused Resource 576

- ID: 576

- Purpose: Unused

## 577. Unused Resource 577

- ID: 577

- Purpose: Unused

## 578. Unused Resource 578

- ID: 578

- Purpose: Unused

## 579. Unused Resource 579

- ID: 579

- Purpose: Unused

## 580. Unused Resource 580

- ID: 580

- Purpose: Unused

## 581. Unused Resource 581

- ID: 581

- Purpose: Unused

## 582. Unused Resource 582

- ID: 582

- Purpose: Unused

## 583. Unused Resource 583

- ID: 583

- Purpose: Unused

## 584. Unused Resource 584

- ID: 584

- Purpose: Unused

## 585. Unused Resource 585

- ID: 585

- Purpose: Unused

## 586. Unused Resource 586

- ID: 586

- Purpose: Unused

## 587. Unused Resource 587

- ID: 587

- Purpose: Unused

## 588. Unused Resource 588

- ID: 588

- Purpose: Unused

## 589. Unused Resource 589

- ID: 589

- Purpose: Unused

## 590. Unused Resource 590

- ID: 590

- Purpose: Unused

## 591. Unused Resource 591

- ID: 591

- Purpose: Unused

## 592. Unused Resource 592

- ID: 592

- Purpose: Unused

## 593. Unused Resource 593

- ID: 593

- Purpose: Unused

## 594. Unused Resource 594

- ID: 594

- Purpose: Unused

## 595. Unused Resource 595

- ID: 595

- Purpose: Unused

## 596. Unused Resource 596

- ID: 596

- Purpose: Unused

## 597. Unused Resource 597

- ID: 597

- Purpose: Unused

## 598. Unused Resource 598

- ID: 598

- Purpose: Unused

## 599. Unused Resource 599

- ID: 599

- Purpose: Unused

## 600. Unused Resource 600

- ID: 600

- Purpose: Unused

---

# 第三部分 任务 Tasks

> 决定单位当前在干什么；`xsTask` / `xsSetTask` 用它。

# Tasks

*Written by: Kramb*

---

This page lists unit task types, the object and task attributes they use, and XS examples where available. If a task or description is incomplete or incorrect, please let the authors of this guide know!

Attributes without an available XS constant are marked **Unavailable**.

## 1. Move to

- XS constant: [cTaskTypeMoveTo](../../xs/constants/constants/#161-ctasktypemoveto)

- Unknown.

## 2. Follow

- XS constant: [cTaskTypeFollow](../../xs/constants/constants/#162-ctasktypefollow)

- Unknown.

## 3. Garrison

- XS constant: [cTaskTypeGarrison](../../xs/constants/constants/#163-ctasktypegarrison)

- Ability to garrison a unit into another unit or building.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cGarrisonCapacity](../../xs/constants/constants/#113-cgarrisoncapacity) | Target object must have some capacity for the current unit to garrison to. |
| [cGarrisonType](../../xs/constants/constants/#1130-cgarrisontype) | If target object is a building, it must have a garrison type that matches current unit's type. |
| [cTraits](../../xs/constants/constants/#1147-ctraits) | If target object is a unit, it must have this bitfield 1st bit (1) set for garrison unit. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Range at which a unit can garrison. |
| [cTaskAttrOwnerType](../../xs/constants/constants/#157-ctaskattrownertype) | Controls which objects the task can target based on ownership. Values: **0** — All objects; **1** — Your objects only; **2** — Neutral and enemy objects only; **3** — Gaia only; **4** — Gaia, your and ally objects only; **5** — Gaia, neutral and enemy objects only; **6** — All but your objects. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Object in which a unit can garrison. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Object in which a unit can garrison. |

XS example

```xs
/* This code gives player 1 scorpion an ability to garrison into friendly castles at a range of 5 */

const int player = 1;
const int scorpion = 279;
const int castle = 82;
const float range = 5.0;
const int garrisonSiegeType = 32;
const int gaiaYouAndAlly = 4;

int currentGarrisonType = xsGetObjectAttribute(player, castle, cGarrisonType);
xsEffectAmount(cSetAttribute, castle, cGarrisonType, currentGarrisonType + garrisonSiegeType, player);

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkRange, range);
xsTaskAmount(cTaskAttrOwnerType, gaiaYouAndAlly);
xsTaskAmount(cTaskAttrTaskType, cTaskTypeGarrison);
xsTaskAmount(cTaskAttrObjectClass, cBuildingClass);

xsModifyObjectTasks(scorpion, player);
```

## 4. Explore

- XS constant: [cTaskTypeExplore](../../xs/constants/constants/#164-ctasktypeexplore)

- Unknown.

## 5. Gather/rebuild

- XS constant: [cTaskTypeGatherRebuild](../../xs/constants/constants/#165-ctasktypegatherrebuild)

- Unknown.

## 6. Graze

- XS constant: [cTaskTypeGraze](../../xs/constants/constants/#166-ctasktypegraze)

- Unknown.

## 7. Combat

- XS constant: [cTaskTypeCombat](../../xs/constants/constants/#167-ctasktypecombat)

- Unknown.

## 8. Shoot

- XS constant: [cTaskTypeShoot](../../xs/constants/constants/#168-ctasktypeshoot)

- Unknown.

## 9. Attack

- XS constant: [cTaskTypeAttack](../../xs/constants/constants/#169-ctasktypeattack)

- Unknown.

## 10. Fly

- XS constant: [cTaskTypeFly](../../xs/constants/constants/#1610-ctasktypefly)

- Unknown.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cStanding2Graphic](../../xs/constants/constants/#1164-cstanding2graphic) | Used instead of the task's **Working graphic (14)**. Graphic while moving, if not set uses moving graphic. |
| [cWalkingGraphic](../../xs/constants/constants/#1167-cwalkinggraphic) | Used if **[Standing Graphic 2 (72)](../../attributes/attributes/#72-standing-graphic-2)** or the task's **Working graphic (14)** is not set. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Unit speed multiplier while roaming. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Unit ID to avoid. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Minimum distance to the unit to avoid that will be maintained while roaming. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | Time in seconds that the unit pauses, playing the idle animations, when changing direction. |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | If set to 1, only roam around if the unit is owned by Gaia. |
| [cTaskAttrTerrain](../../xs/constants/constants/#158-ctaskattrterrain) | Terrain Table that the unit will be allowed to roam on. If -1, use the unit's terrain table. |
| [cTaskAttrMovingGraphic](../../xs/constants/constants/#1513-ctaskattrmovinggraphic) | Graphics used for the unit moving around, randomly alternates between them. |
| [cTaskAttrProceedingGraphic](../../xs/constants/constants/#1514-ctaskattrproceedinggraphic) | Graphics used for the unit moving around, randomly alternates between them. |
| [cTaskAttrWorkingGraphic](../../xs/constants/constants/#1515-ctaskattrworkinggraphic) | Graphics used for the unit moving around, randomly alternates between them. |
| [cTaskAttrCarryCheck](../../xs/constants/constants/#1524-ctaskattrcarrycheck) | Distance the unit is allowed to move from its starting position before picking a new direction to return closer. If 0, no limit. |

## 11. Scare/hunt

- XS constant: 11

- Unknown.

## 12. Unload boat like

- XS constant: [cTaskTypeUnloadBoatLike](../../xs/constants/constants/#1611-ctasktypeunloadboatlike)

- Ability for a unit to unload when reaching certain terrain.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Unknown. |
| [cTaskAttrTerrain](../../xs/constants/constants/#158-ctaskattrterrain) | Terrain on which unit can unload. |

XS example

```xs
/* This code gives player 1 longboats an ability to load and unload friendly berserkers as a transport ship with a capacity of 20. */

const int player = 1;
const int berserk = 692;
const int longboat = 250;
const float range = 1.0;
const int capacity = 20;
const int garrisonUnitTrait = 1;
const int shipUnitTrait = 2;
const int beachTerrain = 2;
const int gaiaYouAndAlly = 4;

xsEffectAmount(cSetAttribute, longboat, cGarrisonCapacity, capacity, player);
xsEffectAmount(cSetAttribute, longboat, cTraits, garrisonUnitTrait + shipUnitTrait, player);

xsResetTaskAmount();
xsTaskAmount(cTaskAttrTerrain, beachTerrain);
xsTask(longboat, cTaskTypeUnloadBoatLike, -1, player);

xsResetTaskAmount();
xsTaskAmount(cTaskAttrWorkRange, range);
xsTaskAmount(cTaskAttrOwnerType, gaiaYouAndAlly);
xsTask(berserk, cTaskTypeGarrison, cWarshipClass, player);
```

## 13. Guard

- XS constant: [cTaskTypeGuard](../../xs/constants/constants/#1612-ctasktypeguard)

- Unknown.

## 14. Unload over wall

- XS constant: [cTaskTypeUnloadOverWall](../../xs/constants/constants/#1613-ctasktypeunloadoverwall)

- Ability for units to unload units over buildings. Only works for walls. For other buildings unit is unloaded on the same side as the task containing unit.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Unknown. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Unknown. |
| [cTaskAttrWorkingGraphic](../../xs/constants/constants/#1515-ctaskattrworkinggraphic) | Graphic of the unit when unloading. |
| [cTaskAttrCarryCheck](../../xs/constants/constants/#1524-ctaskattrcarrycheck) | Unknown. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Building id or class over which to unload units. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Building id or class over which to unload units. |

## 21. Make

- XS constant: [cTaskTypeMake](../../xs/constants/constants/#1614-ctasktypemake)

- Unknown. Related to farms, fishing traps and similar. Maybe the ability to remake them?

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Unknown. |
| [cTaskAttrResourceIn](../../xs/constants/constants/#159-ctaskattrresourcein) | Unknown; resource being collected. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | Unknown, sometimes resource being deposited to. |

## 101. Build

- XS constant: [cTaskTypeBuild](../../xs/constants/constants/#1615-ctasktypebuild)

- Ability for units to build buildings. Building seems hardcoded for villagers and fishing ships. Military units can use this task to build 1 building.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cWorkRate](../../xs/constants/constants/#1113-cworkrate) | Rate at which the unit builds. |
| [cTraits](../../xs/constants/constants/#1147-ctraits) | Set this bitfield 3rd bit (4) to enable military units to build 1 building. |
| [cTraitPiece](../../xs/constants/constants/#1148-ctraitpiece) | Building id to build. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Multiplier for **[Work rate (13)](../../attributes/attributes/#13-work-rate)**. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Build range. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | Unknown. |
| [cTaskAttrProceedingGraphic](../../xs/constants/constants/#1514-ctaskattrproceedinggraphic) | Graphic used while the unit is building. |
| [cTaskAttrWorkingGraphic](../../xs/constants/constants/#1515-ctaskattrworkinggraphic) | Graphic of the unit building a secondary building. |
| [cTaskAttrDepositSound](../../xs/constants/constants/#1520-ctaskattrdepositsound) | Sound id of the unit building. |
| [cTaskAttrAutoSearch](../../xs/constants/constants/#1523-ctaskattrautosearch) | Unknown. |
| [cTaskAttrBuildingPick](../../xs/constants/constants/#1525-ctaskattrbuildingpick) | Unknown. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | For units building 1 building must be the id of the building and match the **[Trait piece (56)](../../attributes/attributes/#56-trait-piece)** field, for villagers this value is -1. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | For units building 1 building must be the id of the building and match the **[Trait piece (56)](../../attributes/attributes/#56-trait-piece)** field, for villagers this value is -1. |

XS example

```xs
/* This code gives player 1 obuch an ability to build fortresses. The unit can build it from a range of 2 and the build rate is its work rate multiplied by 3 */

const int player = 1;
const int obuch = 1701;
const int fortress = 33;
const float workRateMultiplier = 3.0;
const float buildRange = 2.0;
const int obuchAttackGraphic = 12311;
const int enableMilitaryUnitBuilding = 4;

xsEffectAmount(cEnableObject, fortress, cAttributeEnable, 1, player);
xsEffectAmount(cSetAttribute, obuch, cTraits, enableMilitaryUnitBuilding, player);
xsEffectAmount(cSetAttribute, obuch, cTraitPiece, fortress, player);

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, workRateMultiplier);
xsTaskAmount(cTaskAttrWorkRange, buildRange);
xsTaskAmount(cTaskAttrProceedingGraphic, obuchAttackGraphic);
xsTaskAmount(cTaskAttrTaskType, cTaskTypeBuild);
xsTaskAmount(cTaskAttrObjectId, fortress);

xsModifyObjectTasks(obuch, player);
```

## 102. Make unit

- XS constant: [cTaskTypeMakeUnit](../../xs/constants/constants/#1616-ctasktypemakeunit)

- Unknown.

## 103. Make tech

- XS constant: [cTaskTypeMakeTech](../../xs/constants/constants/#1617-ctasktypemaketech)

- Unknown.

## 104. Convert

- XS constant: [cTaskTypeConvert](../../xs/constants/constants/#1618-ctasktypeconvert)

- Ability for units to convert other units. Monks use task attributes, non-monks use object and task attributes. For non-monk units this ability does not work if the unit does not have an attack or similar task already. When adding this task to regular units, existing units will have empty faith bar and will not regenerate, newly created ones will work fine. In addition I did not find a way to add targeting limitations, it seems whatever values are set you can always convert all units and buildings.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cMaxCharge](../../xs/constants/constants/#1151-cmaxcharge) | Amount of value to regenerate to regain conversion ability, usually set to 1. |
| [cRechargeRate](../../xs/constants/constants/#1152-crechargerate) | Amount of charge regenerated per second. |
| [cChargeEvent](../../xs/constants/constants/#1153-cchargeevent) | Conversion range for non-monks. |
| [cChargeType](../../xs/constants/constants/#1154-cchargetype) | Set to -4 to enable conversion for non-monks. |
| [cButtonIconId](../../xs/constants/constants/#11111-cbuttoniconid) | Icon for the conversion button. |
| [cShortTooltipId](../../xs/constants/constants/#11112-cshorttooltipid) | String ID for the conversion button's short tooltip. |
| [cExtendedTooltipId](../../xs/constants/constants/#11113-cextendedtooltipid) | String ID for the conversion button's extended tooltip. |
| [cChargeTarget](../../xs/constants/constants/#11152-cchargetarget) | Conversion percent chance. For example, for 50% set to 50. Not changeable with triggers yet, use task attributes instead. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Minimum conversion time in seconds. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Maximum conversion time in seconds. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Conversion range, if positive takes precedence over object attribute. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | Unknown, for monks it's set to 3091, for buildings 3049, for siege 3093 and for units to 0. Probably somehow related to these abilities being unlocked by research. Maybe unused. |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | Unknown. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | If set associated resource value is a modifier to conversion chance. |
| [cTaskAttrUnusedResource](../../xs/constants/constants/#1512-ctaskattrunusedresource) | If set enable conversion and apply to the conversion range if the associated resource value is greater than 0. |
| [cTaskAttrEnableTargeting](../../xs/constants/constants/#1527-ctaskattrenabletargeting) | Unknown. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Target object or object class to be an eligible target for conversion. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Target object or object class to be an eligible target for conversion. |

## 105. Heal

- XS constant: [cTaskTypeHeal](../../xs/constants/constants/#1619-ctasktypeheal)

- Ability of a unit to heal other units.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cWorkRate](../../xs/constants/constants/#1113-cworkrate) | Rate at which the unit heals. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Multiplier for **[Work rate (13)](../../attributes/attributes/#13-work-rate)**. |
| [cTaskAttrProceedingGraphic](../../xs/constants/constants/#1514-ctaskattrproceedinggraphic) | Graphic used while the unit is healing. |

XS example

```xs
/* This code gives player 1 teutonic knight an ability to heal units. The healing work rate multiplied was set to 5x. */

const int player = 1;
const int teutonicKnight = 25;
const float workRateMultiplier = 5.0;
const float conversionRange = 10.0;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, workRateMultiplier);
xsTaskAmount(cTaskAttrProceedingGraphic, 1160);

xsTask(teutonicKnight, cTaskTypeHeal, -1, player);
```

## 106. Repair

- XS constant: [cTaskTypeRepair](../../xs/constants/constants/#1620-ctasktyperepair)

- Ability for unit to repair buildings or units.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cWorkRate](../../xs/constants/constants/#1113-cworkrate) | Rate at which the unit repairs. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Multiplier for **[Work rate (13)](../../attributes/attributes/#13-work-rate)**. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | Unknown. |
| [cTaskAttrProceedingGraphic](../../xs/constants/constants/#1514-ctaskattrproceedinggraphic) | Graphic used while the unit is repairing. |
| [cTaskAttrWorkingGraphic](../../xs/constants/constants/#1515-ctaskattrworkinggraphic) | Graphic of a unit repairing, seems to be not needed. |
| [cTaskAttrDepositSound](../../xs/constants/constants/#1520-ctaskattrdepositsound) | Sound id of the unit repairing. |
| [cTaskAttrAutoSearch](../../xs/constants/constants/#1523-ctaskattrautosearch) | Unknown. |
| [cTaskAttrBuildingPick](../../xs/constants/constants/#1525-ctaskattrbuildingpick) | Unknown. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | If -1 repairs everything that is repairable, if set repairs that specific object or objects of a class. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | If -1 repairs everything that is repairable, if set repairs that specific object or objects of a class. |

XS example

```xs
/* This code gives player 1 obuch an ability to repair buildings and repairable units. the repair rate is 3 times the work rate. */

const int player = 1;
const int obuch = 1701;
const float workRateMultiplier = 3.0;
const int obuchAttackGraphic = 12311;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, workRateMultiplier);
xsTaskAmount(cTaskAttrProceedingGraphic, obuchAttackGraphic);

xsTask(obuch, cTaskTypeRepair, -1, player);
```

## 107. Get auto-converted

- XS constant: [cTaskTypeGetAutoConverted](../../xs/constants/constants/#1621-ctasktypegetautoconverted)

- Ability to be auto-converted to the player based on that player's other nearby units (e.g., sheep). Does not seem to work on normal units and buildings.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | String ID of a text to display when the unit is converted. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Always -1. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Always -1. |

## 108. Discovery artifact

- XS constant: [cTaskTypeDiscoveryArtifact](../../xs/constants/constants/#1622-ctasktypediscoveryartifact)

- Unknown.

## 110. Hunt

- XS constant: [cTaskTypeHunt](../../xs/constants/constants/#1623-ctasktypehunt)

- Gives the ability to gather resources from map objects and place it into player resources. Since drop sites can't be changed with triggers this task can't be added.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cWorkRate](../../xs/constants/constants/#1113-cworkrate) | Rate at which the unit gathers resources. |
| **Unavailable** — Drop sites | Object at which gathered resources are deposited. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Multiplier for **[Work rate (13)](../../attributes/attributes/#13-work-rate)**. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Gather range. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | Unknown. |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | Unknown. |
| [cTaskAttrOwnerType](../../xs/constants/constants/#157-ctaskattrownertype) | Controls which objects the task can target based on ownership. Values: **0** — All objects; **1** — Your objects only; **2** — Neutral and enemy objects only; **3** — Gaia only; **4** — Gaia, your and ally objects only; **5** — Gaia, neutral and enemy objects only; **6** — All but your objects. |
| [cTaskAttrResourceIn](../../xs/constants/constants/#159-ctaskattrresourcein) | Resource to take from the hunted animal. |
| [cTaskAttrResourceOut](../../xs/constants/constants/#1511-ctaskattrresourceout) | Associated resource to deposit gathered resource into. |
| [cTaskAttrUnusedResource](../../xs/constants/constants/#1512-ctaskattrunusedresource) | If the associated resource value is 1, the hunted corpse does not decay. |
| [cTaskAttrProceedingGraphic](../../xs/constants/constants/#1514-ctaskattrproceedinggraphic) | ID of the graphic used while the unit is attacking. |
| [cTaskAttrWorkingGraphic](../../xs/constants/constants/#1515-ctaskattrworkinggraphic) | ID of the graphic used while the unit is gathering. |
| [cTaskAttrCarryingGraphic](../../xs/constants/constants/#1516-ctaskattrcarryinggraphic) | ID of the graphic used while the unit is carrying resources. |
| [cTaskAttrAutoSearch](../../xs/constants/constants/#1523-ctaskattrautosearch) | If set to 1 unit searches for nearby objects to continuously gather from. |
| [cTaskAttrCarryCheck](../../xs/constants/constants/#1524-ctaskattrcarrycheck) | If set to 1 check if target object has resource before gathering, if set to 0 use Target Diplomacy (6) instead. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | The object to gather from. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | The object to gather from. |

## 111. Trade

- XS constant: [cTaskTypeTrade](../../xs/constants/constants/#1624-ctasktypetrade)

- Adds the ability of the unit to trade for gold with other buildings. Since drop sites can't be changed with triggers this task can't be added.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cWorkRate](../../xs/constants/constants/#1113-cworkrate) | Rate at which the unit trades resources. |
| **Unavailable** — Drop sites | Object to which trade resources are returned. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Multiplier for **[Work rate (13)](../../attributes/attributes/#13-work-rate)**. |
| [cTaskAttrResourceIn](../../xs/constants/constants/#159-ctaskattrresourcein) | Unknown. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | Productivity for secondary trade resource. |
| [cTaskAttrResourceOut](../../xs/constants/constants/#1511-ctaskattrresourceout) | Secondary resource to trade for other than gold when is enabled. |
| [cTaskAttrCarryingGraphic](../../xs/constants/constants/#1516-ctaskattrcarryinggraphic) | ID of the graphic used while the unit is carrying trade resources. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Building to trade with. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Building to trade with. |

## 120. Generate wonder victory

- XS constant: [cTaskTypeGenerateWonderVictory](../../xs/constants/constants/#1625-ctasktypegeneratewondervictory)

- Ability for the object to start a wonder victory timer. Adding it to another object does not seem to work.

## 121. Deselect when tasked

- XS constant: [cTaskTypeDeselectWhenTasked](../../xs/constants/constants/#1626-ctasktypedeselectwhentasked)

- Unknown. Related to farms finishing traps and similar.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Unknown. |
| [cTaskAttrResourceIn](../../xs/constants/constants/#159-ctaskattrresourcein) | Unknown; resource being collected. |

## 122. Loot gather

- XS constant: [cTaskTypeLootGather](../../xs/constants/constants/#1627-ctasktypelootgather)

- Unknown.

## 123. Housing

- XS constant: [cTaskTypeHousing](../../xs/constants/constants/#1628-ctasktypehousing)

- Unknown.

## 124. Pack

- XS constant: [cTaskTypePack](../../xs/constants/constants/#1629-ctasktypepack)

- Unknown.

## 125. Unpack and attack

- XS constant: [cTaskTypeUnpackAndAttack](../../xs/constants/constants/#1630-ctasktypeunpackandattack)

- Ability to unpack from one unit to another and attack. Not possible to add this task with triggers currently.

Object attributes

| XS constant | Description |
| :-- | :-- |
| **Unavailable** — Transform unit | Unit id to transform to. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | Unknown. |
| [cTaskAttrEnableTargeting](../../xs/constants/constants/#1527-ctaskattrenabletargeting) | Unknown. |

## 131. Off map trade

- XS constant: [cTaskTypeOffMapTrade](../../xs/constants/constants/#1631-ctasktypeoffmaptrade)

- Unknown.

## 132. Pickup unit

- XS constant: [cTaskTypePickupUnit](../../xs/constants/constants/#1632-ctasktypepickupunit)

- Ability to pick up targeted objects and turn into a different unit when done. Seems to only work on relics.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Unit id to change into when picking up an object. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Object id to pick up. Seems to ignore this value and only works on relics. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Object id to pick up. Seems to ignore this value and only works on relics. |

XS example

```xs
/* This code gives player 1 mangudai an ability to pick up relics and turn into Genghis Khan. Relics are consumed in the process. */

const int player = 1;
const int mangudai = 11;
const int genghis = 731;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, genghis);
xsTaskAmount(cTaskAttrTaskType, cTaskTypePickupUnit);
xsTaskAmount(cTaskAttrObjectClass, cRelicClass);
xsModifyObjectTasks(mangudai, player);
```

## 133. Charge attack

- XS constant: [cTaskTypeChargeAttack](../../xs/constants/constants/#1633-ctasktypechargeattack)

- Ability to increase the object's speed when closing the distance for an attack.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cMaxCharge](../../xs/constants/constants/#1151-cmaxcharge) | Value added to the attack while charging. Must be at least 1 for the charge to work. |
| [cRechargeRate](../../xs/constants/constants/#1152-crechargerate) | Amount of charge regenerated per second. The charge can be used again when it reaches **[Maximum Charge (59)](../../attributes/attributes/#59-maximum-charge)**. |
| [cChargeEvent](../../xs/constants/constants/#1153-cchargeevent) | Must be 0 or 1 for the task to work. |
| [cChargeType](../../xs/constants/constants/#1154-cchargetype) | Must be 1 for the task to work. |
| [cSpecialAbility](../../xs/constants/constants/#1173-cspecialability) | Must be 3 for the task to work. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Minimum distance from the target for the speed up to start. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Maximum distance from the target for the speed to start. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Multiplier on the unit speed while charging. |
| [cTaskAttrWorkFlag2](../../xs/constants/constants/#154-ctaskattrworkflag2) | Must be 2001 for the task to work. |

XS example

```xs
/* This code gives player 1 knights an ability to charge enemy units, during which they increase their speed by 2.5 times and their attack by 5. This ability has a minimum range of 2, a max range of 7 and a cooldown of 30 seconds. */

const int player = 1;
const int knight = 38;
const float minDistance = 2;
const float maxDistance = 7;
const float speedMultiplier = 2.5;
const int taskEnableFlag = 2001;
const int chargeAbility = 3;
const int chargeEvent = 0;
const int chargeType = 1;
const float chargeAttackBonus = 5.0;
const float cooldownDuration = 30.0;

xsEffectAmount(cSetAttribute, knight, cSpecialAbility, chargeAbility, player);
xsEffectAmount(cSetAttribute, knight, cChargeType, chargeType);
xsEffectAmount(cSetAttribute, knight, cChargeEvent, chargeEvent);
xsEffectAmount(cSetAttribute, knight, cMaxCharge, chargeAttackBonus, player);
xsEffectAmount(cSetAttribute, knight, cRechargeRate, chargeAttackBonus / cooldownDuration, player);

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, minDistance);
xsTaskAmount(cTaskAttrWorkValue2, maxDistance);
xsTaskAmount(cTaskAttrWorkRange, speedMultiplier);
xsTaskAmount(cTaskAttrWorkFlag2, taskEnableFlag);

xsTask(knight, cTaskTypeChargeAttack, -1, player);
```

## 134. Transform unit

- XS constant: [cTaskTypeTransformUnit](../../xs/constants/constants/#1634-ctasktypetransformunit)

- Unknown.

## 135. Kidnap unit

- XS constant: [cTaskTypeKidnapUnit](../../xs/constants/constants/#1635-ctasktypekidnapunit)

- Ability to take an enemy unit and when returning to a town center convert it to your own. Attacking another unit while having a kidnapped unit will release that unit. If a unit has another task that can be performed on a target - this task will not work. Units can be kidnapped on their dying animations but will be returned as corpses.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cGarrisonCapacity](../../xs/constants/constants/#113-cgarrisoncapacity) | Unit must have some capacity to hold a kidnapped unit. |
| **Unavailable** — Task swap group | Will swap the kidnapper into a different unit that also has the same value in this attribute after the kidnapping. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrOwnerType](../../xs/constants/constants/#157-ctaskattrownertype) | Controls which objects the task can target based on ownership. Values: **0** — All objects; **1** — Your objects only; **2** — Neutral and enemy objects only; **3** — Gaia only; **4** — Gaia, your and ally objects only; **5** — Gaia, neutral and enemy objects only; **6** — All but your objects. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Unit id or class id that can be kidnapped. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Unit id or class id that can be kidnapped. |

XS example

```xs
/* This code removes scout attack ability, but gives it an ability to kidnap enemy villagers, and convert them to player 1 when visiting the town center */

const int player = 1;
const int scout = 448;
const int garrisonCapacity = 1;
const int neutralAndEnemy = 2;
const int previousCombatSearchWaitTime = 3;

xsEffectAmount(cSetAttribute, scout, cGarrisonCapacity, garrisonCapacity, player);

xsResetTaskAmount();
xsTaskAmount(cTaskAttrSearchWaitTime, previousCombatSearchWaitTime);
xsRemoveTask(scout, cTaskTypeCombat, -1, player);

xsResetTaskAmount();
xsTaskAmount(cTaskAttrOwnerType, neutralAndEnemy);
xsTaskAmount(cTaskAttrTaskType, cTaskTypeKidnapUnit);
xsTaskAmount(cTaskAttrObjectClass, cVillagerClass);
xsModifyObjectTasks(scout, player);
```

## 136. Deposit unit

- XS constant: [cTaskTypeDepositUnit](../../xs/constants/constants/#1636-ctasktypedepositunit)

- Ability to deposit picked up objects (task 132) into a building and change to a different unit when done. Seems to only work on relics.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Unit id to change into when depositing an object. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Building id to deposit the picked up object to, does not seem to work with custom units. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Building id to deposit the picked up object to, does not seem to work with custom units. |

## 149. Shear

- XS constant: [cTaskTypeShear](../../xs/constants/constants/#1637-ctasktypeshear)

- Unknown.

## 151. Generate resources

- XS constant: [cTaskTypeGenerateResources](../../xs/constants/constants/#1638-ctasktypegenerateresources)

- Ability of an object to gain resources when attacking or idling.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Amount of resources received. |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | For units, set to 2 to generate resources passively. Buildings always generate resources passively. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | The value of this resource is used as a multiplier of the amount received. Must be set to some resource containing a positive value for the task to work. |
| [cTaskAttrResourceOut](../../xs/constants/constants/#1511-ctaskattrresourceout) | Resource type to receive. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Object which if attacked by a unit will generate resource. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Object which if attacked by a unit will generate resource. |

XS example

```xs
/* This code makes player 1 Attila the Hun gain gold when attacking enemy infantry, archer or cavalry units */

const int player = 1;
const int attila = 777;
const float resourceGainRate = 1.0;
const int resourceToGain = cAttributeGold;
const int productivityResource = 600;
const float productivity = 1.0;

xsSetPlayerAttribute(player, productivityResource, productivity);

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, resourceGainRate);
xsTaskAmount(cTaskAttrProductivityResource, productivityResource);
xsTaskAmount(cTaskAttrResourceOut, resourceToGain);

xsTaskAmount(cTaskAttrTaskType, cTaskTypeGenerateResources);

xsTaskAmount(cTaskAttrObjectClass, cInfantryClass);
xsModifyObjectTasks(attila, player);

xsTaskAmount(cTaskAttrObjectClass, cArcherClass);
xsModifyObjectTasks(attila, player);

xsTaskAmount(cTaskAttrObjectClass, cCavalryClass);
xsModifyObjectTasks(attila, player);
```

## 152. Movement damage

- XS constant: [cTaskTypeMovementDamage](../../xs/constants/constants/#1639-ctasktypemovementdamage)

- Ability for a unit to damage surrounding enemy units while moving.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Amount of damage to deal per tick. If negative will increase the current HP instead. Will go over max HP. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | How often the unit damages surrounding units in fraction of seconds. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Range of this damage surrounding the current unit. |

XS example

```xs
/* This code gives player 1 war elephant an ability to damage enemy units while moving in a 0.75 range twice per second for 2.5 damage */

const int player = 1;
const int elephant = 239;
const float damage = 2.5;
const float time = 0.5;
const float range = 0.75;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, damage);
xsTaskAmount(cTaskAttrWorkValue2, time);
xsTaskAmount(cTaskAttrWorkRange, range);

xsTask(elephant, cTaskTypeMovementDamage, -1, player);
```

## 153. Movable dropsite

- XS constant: [cTaskTypeMovableDropsite](../../xs/constants/constants/#1640-ctasktypemovabledropsite)

- Ability for a unit to be a movable dropsite. For this task to work this unit needs to be added for the worker unit as a dropsite (currently not possible with triggers or XS).

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | Unknown. |
| [cTaskAttrCarryCheck](../../xs/constants/constants/#1524-ctaskattrcarrycheck) | Unknown. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Resources containing object for which this unit exists as a dropsite. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Resources containing object for which this unit exists as a dropsite. |

## 154. Loot

- XS constant: [cTaskTypeLoot](../../xs/constants/constants/#1641-ctasktypeloot)

- Ability of an object to gain resources and attributes after killing or converting an object.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Amount of resources received. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | If set to 0 applies to all units. If set to >0 then it applies to only units whose player matches this value. |
| [cTaskAttrWorkFlag2](../../xs/constants/constants/#154-ctaskattrworkflag2) | If set, maximum number of times this unit can trigger the task. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | ID of the object attribute modified by this task. Attributes known to be supported include: **[Hit points (0)](../../attributes/attributes/#0-hit-points),** **[Attack (9)](../../attributes/attributes/#9-attack)**. |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | If set to 1, unit will gain attributes. |
| [cTaskAttrResourceIn](../../xs/constants/constants/#159-ctaskattrresourcein) | If set the tech of the associated resources value id will be researched. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | If positive, the associated resource value must be greater than 0 for this task to activate. The positive value multiplies the resources gained. If negative, its absolute value is treated as a technology ID, and that technology must be researched for this task to activate. |
| [cTaskAttrResourceOut](../../xs/constants/constants/#1511-ctaskattrresourceout) | Resource type to receive. |
| [cTaskAttrUnusedResource](../../xs/constants/constants/#1512-ctaskattrunusedresource) | If set the tech of the associated resources value id will be researched. |
| [cTaskAttrProceedingGraphic](../../xs/constants/constants/#1514-ctaskattrproceedinggraphic) | Graphic that plays when the unit gains an attribute via the task. |
| [cTaskAttrCarryCheck](../../xs/constants/constants/#1524-ctaskattrcarrycheck) | If set, all Tasks 154 with the same Carry Check ID will count towards the same cap. |
| [cTaskAttrGatherType](../../xs/constants/constants/#1526-ctaskattrgathertype) | If unit gains attributes this attribute stores the amount of attribute the unit gains. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Object which if killed by this unit will trigger resource/attribute gain. If -1 affects all units. Has to be an object that can increase the kill/razing/conversions stats. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Object which if killed by this unit will trigger resource/attribute gain. If -1 affects all units. Has to be an object that can increase the kill/razing/conversions stats. |

XS example 1

```xs
/* This code makes player 1 Attila the Hun gain 2 gold when killing enemy unit or destroying an enemy building */

const int player = 1;
const int attila = 777;
const float resourceGainRate = 2.0;
const int resourceToGain = cAttributeGold;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, resourceGainRate);
xsTaskAmount(cTaskAttrResourceOut, resourceToGain);

xsTask(attila, cTaskTypeLoot, -1, player);
```

XS example 2

```xs
/* This code makes player 1 mangudai gain 1 attack every time they kill an infantry, archer, cavalry or siege unit to a maximum of 5 */

const int player = 1;
const int mangudai = 11;
const int maxNumberOfStatGains = 5;
const int gainAttributesFlag = 1;
const int attribute = cAttack;
const float amountToGain = 1.0;
const int levelUpGraphic = 12263;
const int statGainId = 1;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrTaskType, cTaskTypeLoot);
xsTaskAmount(cTaskAttrWorkFlag2, maxNumberOfStatGains);
xsTaskAmount(cTaskAttrSearchWaitTime, attribute);
xsTaskAmount(cTaskAttrCombatLevelFlag, gainAttributesFlag);
xsTaskAmount(cTaskAttrProceedingGraphic, levelUpGraphic);
xsTaskAmount(cTaskAttrCarryCheck, statGainId);
xsTaskAmount(cTaskAttrGatherType, amountToGain);

xsTaskAmount(cTaskAttrObjectClass, cInfantryClass);
xsModifyObjectTasks(mangudai, player);

xsTaskAmount(cTaskAttrObjectClass, cArcherClass);
xsModifyObjectTasks(mangudai, player);

xsTaskAmount(cTaskAttrObjectClass, cCavalryClass);
xsModifyObjectTasks(mangudai, player);

xsTaskAmount(cTaskAttrObjectClass, cSiegeWeaponClass);
xsModifyObjectTasks(mangudai, player);
```

## 155. Aura

- XS constant: [cTaskTypeAura](../../xs/constants/constants/#1642-ctasktypeaura)

- Auras are stat modifiers that affect all objects surrounding the aura object (or the aura object itself).

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cRechargeRate](../../xs/constants/constants/#1152-crechargerate) | Amount of charge regenerated per second. Together with **[Maximum Charge (59)](../../attributes/attributes/#59-maximum-charge)**, this controls the temporary aura's cooldown. The cooldown ends when the charge reaches **[Maximum Charge (59)](../../attributes/attributes/#59-maximum-charge)**. For a 60-second cooldown, set **[Maximum Charge (59)](../../attributes/attributes/#59-maximum-charge)** to 1 and **[Recharge rate (60)](../../attributes/attributes/#60-recharge-rate)** to 0.01666667 (1.0 / 60.0). |
| [cChargeEvent](../../xs/constants/constants/#1153-cchargeevent) | For temporary auras stores aura duration when activated. |
| [cChargeType](../../xs/constants/constants/#1154-cchargetype) | Set to -3 to enable temporary auras. |
| [cCombatAbility](../../xs/constants/constants/#1155-ccombatability) | Attribute bitfield 6th bit (32) needs to be set for the aura to activate. If 7th bit is set (64) the aura will affect the unit itself instead of the units in range (aura prerequisites still need to be met on other units). |
| [cButtonIconId](../../xs/constants/constants/#11111-cbuttoniconid) | Icon for the temporary aura button. |
| [cShortTooltipId](../../xs/constants/constants/#11112-cshorttooltipid) | String ID for the temporary aura button's short tooltip. |
| [cExtendedTooltipId](../../xs/constants/constants/#11113-cextendedtooltipid) | String ID for the temporary aura button's extended tooltip. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Aura attribute value to add or multiply. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Minimum amount of units to be in range for the aura to activate. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | Aura range. If aura targets enemies the targeted enemy units must be in range of aura units sight range. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | ID of the object attribute modified by this task. Attributes known to be supported include: [Hit points (0)](../../attributes/attributes/#0-hit-points), [Line of sight (1)](../../attributes/attributes/#1-line-of-sight), [Movement speed (5)](../../attributes/attributes/#5-movement-speed), [Attack (9)](../../attributes/attributes/#9-attack), [Attack reload time (10)](../../attributes/attributes/#10-attack-reload-time), [Maximum Range (12)](../../attributes/attributes/#12-maximum-range) (visual only), [Work rate (13)](../../attributes/attributes/#13-work-rate), [Regeneration rate (109)](../../attributes/attributes/#109-regeneration-rate), [Conversion chance modifier (113)](../../attributes/attributes/#113-conversion-chance-modifier), Melee armor (116), Pierce armor (117), [Regeneration HP percent (120)](../../attributes/attributes/#120-regeneration-hp-percent). |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | Bit field of aura settings: **multiply (1)** multiplies attribute value instead of adds it, **circular (2)** makes aura range circular instead of square, **visible (4)** shows range indicator (is affected by ui settings), **temporary (8)** makes aura effect temporary, **activated (16)** the temporary effect is only applied on the moment of aura activation, and remains if target units leave the aura, **translucent (32)** make aura indicator translucent, unsure how it works as its overwritten by ui settings. |
| [cTaskAttrOwnerType](../../xs/constants/constants/#157-ctaskattrownertype) | Controls which objects the task can target based on ownership. Values: **0** — All objects; **1** — Your objects only; **2** — Neutral and enemy objects only; **3** — Gaia only; **4** — Gaia, your and ally objects only; **5** — Gaia, neutral and enemy objects only; **6** — All but your objects. |
| [cTaskAttrProceedingGraphic](../../xs/constants/constants/#1514-ctaskattrproceedinggraphic) | Graphic displayed over the units receiving the aura. |
| [cTaskAttrGatheringSound](../../xs/constants/constants/#1517-ctaskattrgatheringsound) | Short Tooltip for UI indicator. |
| [cTaskAttrDepositSound](../../xs/constants/constants/#1520-ctaskattrdepositsound) | Long Tooltip for UI indicator. |
| [cTaskAttrGatherType](../../xs/constants/constants/#1526-ctaskattrgathertype) | UI indicator icon displayed (per icons.json). |
| [cTaskAttrEnabled](../../xs/constants/constants/#1528-ctaskattrenabled) | If set, the associated resource value needs to be set to >0 for the aura to activate. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Object targeted by the aura. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Object targeted by the aura. |

XS example 1

```xs
/* This code makes player 1 Joan of Arc give friendly infantry, archer and cavalry units within 10 range +5 to their attack */

const int player = 1;
const int joanOfArc = 629;
const int unitsInRangeToActivate = 1;
const float auraRange = 10.0;
const int attribute = cAttack;
const int value = 5;
const int gaiaYouAndAlly = 4;
const int circularFlag = 2;
const int visibleFlag = 4;
const int translucentFlag = 32;
const int auraAbility = 32;

xsEffectAmount(cSetAttribute, joanOfArc, cCombatAbility, auraAbility, player);

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, value);
xsTaskAmount(cTaskAttrWorkValue2, unitsInRangeToActivate);
xsTaskAmount(cTaskAttrWorkRange, auraRange);
xsTaskAmount(cTaskAttrSearchWaitTime, attribute);
xsTaskAmount(cTaskAttrCombatLevelFlag, circularFlag + visibleFlag + translucentFlag);
xsTaskAmount(cTaskAttrOwnerType, gaiaYouAndAlly);

xsTaskAmount(cTaskAttrTaskType, cTaskTypeAura);

xsTaskAmount(cTaskAttrObjectClass, cInfantryClass);
xsModifyObjectTasks(joanOfArc, player);

xsTaskAmount(cTaskAttrObjectClass, cArcherClass);
xsModifyObjectTasks(joanOfArc, player);

xsTaskAmount(cTaskAttrObjectClass, cCavalryClass);
xsModifyObjectTasks(joanOfArc, player);
```

XS example 2

```xs
/* This code makes player 1 Joan of Arc double the movement speed of friendly infantry, archers and cavalry units in range of 10 for 30 seconds, with a 60 second cooldown. Units can leave the aura range and still have the speed increase. */

const int player = 1;
const int joanOfArc = 629;
const int unitsInRangeToActivate = 1;
const float auraRange = 10.0;
const int attribute = cMovementSpeed;
const float value = 2.0;
const int gaiaYouAndAlly = 4;
const int multiplyFlag = 1;
const int circularFlag = 2;
const int temporaryAuraFlag = 8;
const int remainsWhenLeavingRangeFlag = 16;
const int auraAbility = 32;
const int enableTempAuraType = -3;
const float tempAuraDuration = 30.0;
const float tempAuraCooldown = 60.0;
const float maximumCharge = 1.0;
const int buttonIcon = 98;

xsEffectAmount(cSetAttribute, joanOfArc, cCombatAbility, auraAbility, player);

xsEffectAmount(cSetAttribute, joanOfArc, cChargeType, enableTempAuraType, player);
xsEffectAmount(cSetAttribute, joanOfArc, cChargeEvent, tempAuraDuration, player);
xsEffectAmount(cSetAttribute, joanOfArc, cMaxCharge, maximumCharge, player);
xsEffectAmount(cSetAttribute, joanOfArc, cRechargeRate, maximumCharge / tempAuraCooldown, player);
xsEffectAmount(cSetAttribute, joanOfArc, cButtonIconId, buttonIcon, player);

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, value);
xsTaskAmount(cTaskAttrWorkValue2, unitsInRangeToActivate);
xsTaskAmount(cTaskAttrWorkRange, auraRange);
xsTaskAmount(cTaskAttrSearchWaitTime, attribute);
xsTaskAmount(cTaskAttrCombatLevelFlag, multiplyFlag + circularFlag + temporaryAuraFlag + remainsWhenLeavingRangeFlag);
xsTaskAmount(cTaskAttrOwnerType, gaiaYouAndAlly);

xsTaskAmount(cTaskAttrTaskType, cTaskTypeAura);

xsTaskAmount(cTaskAttrObjectClass, cInfantryClass);
xsModifyObjectTasks(joanOfArc, player);

xsTaskAmount(cTaskAttrObjectClass, cArcherClass);
xsModifyObjectTasks(joanOfArc, player);

xsTaskAmount(cTaskAttrObjectClass, cCavalryClass);
xsModifyObjectTasks(joanOfArc, player);
```

## 156. Additional spawn

- XS constant: [cTaskTypeExtraSpawn](../../xs/constants/constants/#1643-ctasktypeextraspawn)

- Spawns additional units when the unit is trained.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Id of an additional unit to spawn. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Number of units to spawn. |
| [cTaskAttrResourceIn](../../xs/constants/constants/#159-ctaskattrresourcein) | If set, the value of the corresponding resource needs to be >0 for the Task to trigger. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | If set, the associated resource value is added to the number of units to spawn. |

XS example

```xs
/* This code makes that every time a huskarl unit is spawned for player 1, 2 additional spearline units are also spawned from the same source. */

const int player = 1;
const int huskarl = 41;
const int spearman = 93;
const int amount = 2;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, spearman);
xsTaskAmount(cTaskAttrWorkValue2, amount);

xsTask(huskarl, cTaskTypeExtraSpawn, -1, player);
```

## 157. Stinger

- XS constant: [cTaskTypeStinger](../../xs/constants/constants/#1644-ctasktypestinger)

- Stingers are stat modifiers applied on a unit being attacked or the attacking unit.

Object attributes

| XS constant | Description |
| :-- | :-- |
| [cCombatAbility](../../xs/constants/constants/#1155-ccombatability) | Attribute bitfield 8th bit (128) needs to be set for stingers to activate. |

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Stingers attribute value to add or multiply. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Effect duration in seconds, if negative it's permanent. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | If 0 apply to the attacker, if 1 apply to the target of the attack (including splash damage targets). |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | ID of the object attribute modified by this task. Attributes known to be supported include: **[Hit points (0)](../../attributes/attributes/#0-hit-points), [Movement speed (5)](../../attributes/attributes/#5-movement-speed), [Attack (9)](../../attributes/attributes/#9-attack), [Attack reload time (10)](../../attributes/attributes/#10-attack-reload-time), [Regeneration rate (109)](../../attributes/attributes/#109-regeneration-rate), Melee armor (116), Pierce armor (117), [Regeneration HP percent (120)](../../attributes/attributes/#120-regeneration-hp-percent)**. |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | Bit field of stingers settings: **Multiply (1)** multiplies attribute value instead of adds it, **Not stack (2)** does not allow other stinger tasks that modify same attribute to stack. |
| [cTaskAttrOwnerType](../../xs/constants/constants/#157-ctaskattrownertype) | Controls which objects the task can target based on ownership. Values: **0** — All objects; **1** — Your objects only; **2** — Neutral and enemy objects only; **3** — Gaia only; **4** — Gaia, your and ally objects only; **5** — Gaia, neutral and enemy objects only; **6** — All but your objects. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | If positive, the associated resource value must be greater than 0 for this task to activate. |
| [cTaskAttrObjectId](../../xs/constants/constants/#1530-ctaskattrobjectid) | Object targeted by the stinger. |
| [cTaskAttrObjectClass](../../xs/constants/constants/#1531-ctaskattrobjectclass) | Object targeted by the stinger. |

XS example

```xs
/* This code makes player 1 Joan of Arc slow infantry, archer and
cavalry units she attacks to 20% of their speed for 5 seconds */

const int player = 1;
const int joanOfArc = 629;
const float value = -0.8;
const float duration = 5.0;
const int affectTarget = 1;
const int attribute = cMovementSpeed;
const int multiplyFlag = 1;
const int dontStackFlag = 2;
const int stingerAbility = 128;

xsEffectAmount(cSetAttribute, joanOfArc, cCombatAbility, stingerAbility, player);

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, value);
xsTaskAmount(cTaskAttrWorkValue2, duration);
xsTaskAmount(cTaskAttrWorkRange, affectTarget);
xsTaskAmount(cTaskAttrSearchWaitTime, attribute);
xsTaskAmount(cTaskAttrCombatLevelFlag, multiplyFlag + dontStackFlag);

xsTaskAmount(cTaskAttrTaskType, cTaskTypeStinger);

xsTaskAmount(cTaskAttrObjectClass, cInfantryClass);
xsModifyObjectTasks(joanOfArc, player);

xsTaskAmount(cTaskAttrObjectClass, cArcherClass);
xsModifyObjectTasks(joanOfArc, player);

xsTaskAmount(cTaskAttrObjectClass, cCavalryClass);
xsModifyObjectTasks(joanOfArc, player);
```

## 158. HP transformation

- XS constant: [cTaskTypeHPTransform](../../xs/constants/constants/#1645-ctasktypehptransform)

- Transform into another unit based on current HP.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | ID of the unit to transform to. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | HP to trigger the transformation. If >0 transforms when the unit's current HP is higher than the value. If XS example

```xs
/* This code makes player 1 karambit warrior transform into a berserk when under 40% hp, and transform back when above 60% using level up graphic */

const int player = 1;
const int karambit = 1123;
const int berserk = 692;
const float transformAtPercent = -0.4;
const float transformBackPercent = 0.6;
const int multiplyFlag = 1;
const int levelUpGraphic = 12263;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, berserk);
xsTaskAmount(cTaskAttrWorkValue2, transformAtPercent);
xsTaskAmount(cTaskAttrCombatLevelFlag, multiplyFlag);
xsTaskAmount(cTaskAttrProceedingGraphic, levelUpGraphic);

xsTask(karambit, cTaskTypeHPTransform, -1, player);

xsTaskAmount(cTaskAttrWorkValue1, karambit);
xsTaskAmount(cTaskAttrWorkValue2, transformBackPercent);

xsTask(berserk, cTaskTypeHPTransform, -1, player);
```

## 159. Amphibious

- XS constant: [cTaskTypeAmphibious](../../xs/constants/constants/#1646-ctasktypeamphibious)

- Unit changes graphics based on current terrain.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Movement Speed multiplier. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Attack Speed multiplier. |
| [cTaskAttrTerrain](../../xs/constants/constants/#158-ctaskattrterrain) | Terrain (or Terrain Type) on which the unit will use the task. If >= 0: Terrain ID. If Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Value to add. |
| [cTaskAttrWorkValue2](../../xs/constants/constants/#152-ctaskattrworkvalue2) | Threshold of HP percentage to apply the modifier. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | If 0, check the unit's own HP. If > 0, compare the current target's HP. |
| [cTaskAttrSearchWaitTime](../../xs/constants/constants/#155-ctaskattrsearchwaittime) | ID of the object attribute modified by this task. Attributes known to be supported include: **[Attack (9)](../../attributes/attributes/#9-attack)**. |

XS example

```xs
/* This code makes player 1 throwing axeman unit gain +2 attack for each 20% of hp that it lost */

const int player = 1;
const int throwingAxeman = 281;
const int value = 2;
const float hpPercent = 0.2;
const int compareToTargetHp = 0;
const int attribute = cAttack;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, value);
xsTaskAmount(cTaskAttrWorkValue2, hpPercent);
xsTaskAmount(cTaskAttrWorkRange, compareToTargetHp);
xsTaskAmount(cTaskAttrSearchWaitTime, attribute);

xsTask(throwingAxeman, cTaskTypeHPModifier, -1, player);
```

## 161. Unit refund

- XS constant: [cTaskTypeRefund](../../xs/constants/constants/#1648-ctasktyperefund)

- Resource to grant on death.

Task attributes

| XS constant | Description |
| :-- | :-- |
| [cTaskAttrWorkValue1](../../xs/constants/constants/#151-ctaskattrworkvalue1) | Value to refund. |
| [cTaskAttrWorkRange](../../xs/constants/constants/#153-ctaskattrworkrange) | If 0, grant the resources to the player who owned the unit. If > 0, grant to the player who killed the unit. |
| [cTaskAttrCombatLevelFlag](../../xs/constants/constants/#156-ctaskattrcombatlevelflag) | If 0, use Work Value 1 as a flat value to grant. If 1, use Work Value 1 as a fraction of the unit's associated resource cost. |
| [cTaskAttrProductivityResource](../../xs/constants/constants/#1510-ctaskattrproductivityresource) | If set, multiply Work Value 1 by the value of this resource. |
| [cTaskAttrResourceOut](../../xs/constants/constants/#1511-ctaskattrresourceout) | Resource to refund. |

XS example

```xs
/* This code makes 10 gold be refunded to player 1 when a monk unit is killed */

const int player = 1;
const int monk = 125;
const int monkWithRelic = 286;
const int value = 10;
const int grantToKiller = 0;
const int valueIsFractionOfCost = 0;
const int resource = cAttributeGold;

xsResetTaskAmount();

xsTaskAmount(cTaskAttrWorkValue1, value);
xsTaskAmount(cTaskAttrWorkRange, grantToKiller);
xsTaskAmount(cTaskAttrCombatLevelFlag, valueIsFractionOfCost);
xsTaskAmount(cTaskAttrResourceOut, resource);

xsTask(monk, cTaskTypeRefund, -1, player);
xsTask(monkWithRelic, cTaskTypeRefund, -1, player);
```

---

# 第四部分 伤害计算 Damage Calculation

> 护甲/攻击/加成类的完整公式推导，是判断「改哪个 class 才有用」的唯一权威。

# The Armour & Attack Class System: The Backbone of Age of Empires II
*Written by: Alian713*

---

Foreword: This page is quite outdated, and no longer accurately reflects the damage calculation algorithm. It is majorly still correct as this algorithm is still the foundation for the system, but additional attributes affect the calculation too which are not discussed here.

## 1. The Purpose

Have you ever wondered how bonus damage works in AoE2? How does a Halberdier get its +32 damage against cavalry? How does a Cataphract only take +16 damage from Halbderdiers instead of the full 32? And finally, how could **you** give bonus damage or armour against bonus damage to units for yourself? Lets find the answers to these questions by learning about the armour and attack class system of AoE2

## 2. Why do you, a map maker, need to know this?

Understanding how damage calculation works and how attacks from one unit to another are calculated is essential for modding and using some of the effects in triggers. Aside from that, it is quite interesting in itself to know how damage is calculated behind the scenes in the game.

## 3. The System

### 3.1. Introduction

Each unit in the game has two essential properties, a list of `Attack Classes` and a list of `Armour Classes`. These are also commonly called the `Damage Classes`, and are used to calculate the damage each unit does to any other unit. There are a total of 36 damage classes in the game but pierce and melee damage classes are the most commonly known ones, as they are the only ones which are actually shown in game. There is also a 3rd property that we need to know about, which is the `Base Armour`. This is almost always set to 1000 for every unit.

### 3.2. List of Damage Classes

The following are all the damage classes along with their IDs that exist in the game: (Note that the Armour Classes have the same names and ids as the Attack classes, the reason for this will become clear once you read through the explanation provided below)

|          **Class Name**         | **ID** |
| :-----------------------------: | :----: |
| Wonder                          |   0    |
| Infantry                        |   1    |
| Turtle Ships                    |   2    |
| Base Pierce                     |   3    |
| Base Melee                      |   4    |
| War Elephants                   |   5    |
| Unused                          |   6    |
| Unused                          |   7    |
| Cavalry                         |   8    |
| Unused                          |   9    |
| Unused                          |   10   |
| All Buildings (except Port)     |   11   |
| Unused                          |   12   |
| Stone Defense                   |   13   |
| Predator Animals                |   14   |
| Archers                         |   15   |
| Ships Saboteers (camels pre AK) |   16   |
| Rams Trebuchets Siege Towers    |   17   |
| Trees                           |   18   |
| Unique Units                    |   19   |
| Siege Weapons                   |   20   |
| Standard Buildings              |   21   |
| Walls & Gates                   |   22   |
| Gunpowder Units                 |   23   |
| Hunted Predator Animals         |   24   |
| Monks                           |   25   |
| Castles                         |   26   |
| Spearmen                        |   27   |
| Cavalry Archers                 |   28   |
| Eagle Warriors                  |   29   |
| Camels (post AK)                |   30   |
| Unused                          |   31   |
| Condottieri                     |   32   |
| Projectile Gunpowder Secondary  |   33   |
| Fishing Ships                   |   34   |
| Mamelukes                       |   35   |
| Heroes and Kings                |   36   |
| Hussite Wagons                  |   37   |

The explanation of how this system works is given using the example of a Halberdier vs War Elephant, but this method is a general method applicable to any two units fighting each other
(At first glance, all of this may seem daunting, but it will get clearer as we walk through the two examples given below!)

### 3.3. Explanation Using Maths

The case of the Halberdier attacking the War Elephant:

| **Attack Classes Halberdier**| **Quantity**|      | **Armour Classes War Elephant**| **Quantity**|
| :-----------                 | :---------: |      | :-----------                   | :---------: |
| -                            |   -         |      | 3  (Base Pierce)               |   2         |
| 4  (Base Melee)              |   6         |      | 4  (Base Melee)                |   1         |
| 5  (War Elephants)           |   28        |      | 5  (War Elephants)             |   0         |
| 8  (Cavalry)                 |   32        |      | 8  (Cavalry)                   |   0         |
| 16 (Ships & Saboteers)       |   17        |      | -                              |   17        |
| -                            |   -         |      | 19 (Unique Units)              |   17        |
| 21 (Standard Buildings)      |   1         |      | -                              |   -         |
| 29 (Eagle Warriors)          |   1         |      | -                              |   -         |
| 30 (Camels)                  |   26        |      | -                              |   -         |
| -                            |   -         |      | 31 (Unused)                    |   26        |
| 34 (Fishing Ship)            |   17        |      | -                              |   -         |
| 35 (Mamelukes)               |   11        |      | -                              |   -         |

Here you can see all the attack classes listed out for the Halberdier and the armour classes listed out for the War Elephant.

For calculating the total amount of damage that this unupgraded Halberdier deals to the unupgraded War Elephant, we go through these steps given below:

1. Identify the damage classes that are in common for the attacking unit's attack class list and the defending unit's armour class list.

    The damage classes which are in common are: `Base Melee (4)`, `War Elephants (5)` and `Cavalry (8)` (they are also highlighted in the table above) for which the War Elephant has armour classes and the Halberdier has attack classes.

2. For each damage class that is in common, subtract the armour of the defending unit from the attack of the attacking unit. Round up to 0 if you get a negative value.

    Here, $\color{yellow} Ar_i$ is the quantity of the armour class with id $i$ for the War Elephant. For example, $\color{yellow} Ar_{19}$ refers to the `Unique Units` armour class of the War Elephant.
    $\color{#bfe3b4} At_i$ is the quantity of the attack class with id $i$ for the Halberdier. For example, $\color{#bfe3b4} At_{16}$ refers to the `Ships and saboteer` attack class of the Halberdier. $\color{yellow} Ba$ is the Base Armour value for the defending unit, the war elephant.

    (Note that the ids for every armour class in the game can be found in the table under the topic 3.2.)

    Melee Damage Class:

    $\text{dmg}_4 =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_4-\color{yellow} Ar_4, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_4 = \color{#ff6961}\text{max}( \color{#bfe3b4} 6-\color{yellow} 1, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_4 = \color{#ff6961}\text{max}( \color{#bfe3b4} 5, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_4 = \color{#ff6961} 5$

    War Elephant Damage Class:

    $\text{dmg}_5 =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_5-\color{yellow} Ar_5, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_5 = \color{#ff6961}\text{max}( \color{#bfe3b4} 28-\color{yellow} 0, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_5 = \color{#ff6961}\text{max}( \color{#bfe3b4} 28, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_5 = \color{#ff6961} 28$

    Cavalry Damage Class:

    $\text{dmg}_8 =  \color{#ff6961}\text{max}( \color{#bfe3b4} Ar_8-\color{yellow} At_8, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_8 = \color{#ff6961}\text{max}( \color{#bfe3b4} 32-\color{yellow} 0, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_8 = \color{#ff6961}\text{max}( \color{#bfe3b4} 32, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_8 = \color{#ff6961} 32$

3. For each attack class of the attacking unit for which there is no armour class for the defending unit, we use the base armour value to calculate how much attack needs to be dealt.

    Ships & Saboteers Damage Class:

    $\text{dmg}_{16} =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_{16}-\color{yellow} Ba, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{16} = \color{#ff6961}\text{max}( \color{#bfe3b4} 17-\color{yellow} 1000, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{16} = \color{#ff6961}\text{max}( \color{#bfe3b4} -983, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{16} = \color{#ff6961} 0$

    Standard Buildings:

    $\text{dmg}_{21} =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_{21}-\color{yellow} Ba, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{21} = \color{#ff6961}\text{max}( \color{#bfe3b4} 1-\color{yellow} 1000, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{21} = \color{#ff6961}\text{max}( \color{#bfe3b4} -999, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{21} = \color{#ff6961} 0$

    Eagle Warriors:

    $\text{dmg}_{29} =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_{29}-\color{yellow} Ba, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{29} = \color{#ff6961}\text{max}( \color{#bfe3b4} 1-\color{yellow} 1000, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{29} = \color{#ff6961}\text{max}( \color{#bfe3b4} -999, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{29} = \color{#ff6961} 0$

    Camels:

    $\text{dmg}_{30} =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_{30}-\color{yellow} Ba, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{30} = \color{#ff6961}\text{max}( \color{#bfe3b4} 26-\color{yellow} 1000, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{30} = \color{#ff6961}\text{max}( \color{#bfe3b4} -974, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{30} = \color{#ff6961} 0$

    Fishing Ships:

    $\text{dmg}_{34} =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_{34}-\color{yellow} Ba, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{34} = \color{#ff6961}\text{max}( \color{#bfe3b4} 17-\color{yellow} 1000, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{34} = \color{#ff6961}\text{max}( \color{#bfe3b4} -983, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{34} = \color{#ff6961} 0$

    Fishing Ships:

    $\text{dmg}_{35} =  \color{#ff6961}\text{max}( \color{#bfe3b4} At_{35}-\color{yellow} Ba, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{35} = \color{#ff6961}\text{max}( \color{#bfe3b4} 11-\color{yellow} 1000, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{35} = \color{#ff6961}\text{max}( \color{#bfe3b4} -989, \; \color{white} 0 \color{#ff6961})$

    $\text{dmg}_{35} = \color{#ff6961} 0$

    Trick: Remember, the value for `Base Armour` is almost always 1000, so unless the unit has an attack of more than 1000 in an attack class, they practically have no effect on the amount of damage dealt! This above calculation with base armour can thus be skipped if that is the case

4. Now add all of the differences found above. Round up to 1 if you get 0.

    $\text{dmg} = \color{#add8e6} \text{max}( \color{#bfe3b4} \text{dmg}_4 + \text{dmg}_5 + \text{dmg}_8 +$

    $\;\;\;\;\;\;\;\;\;\;\;\;\;\;\;\;\;\;\;\;\color{#bfe3b4}\text{dmg}_{16} + \text{dmg}_{21} + \text{dmg}_{29} + \text{dmg}_{30} + \text{dmg}_{34} + \text{dmg}_{35}, \; \color{#bfe3b4} 1 \color{#add8e6})$

    $\text{dmg} = \color{#add8e6} \text{max}( \color{#bfe3b4} 5+28+32+0, \; \color{#bfe3b4} 1 \color{#add8e6})$

    $\text{dmg} = \color{#add8e6} \text{max}( \color{#bfe3b4} 65, \; \color{#bfe3b4} 1 \color{#add8e6})$

    $\text{dmg} = 65$

5. The value thus obtained is the damage that the Halberdier deals to the War Elephant.

The General formula for damage calculation between any two units is thus:

if $\color{#a66fb5} D$ is the set of all attack classes for the attacking unit,

$\color{#bfe3b4} At_i$ is the quanitity of the attack class with id $i$ for the attacking unit. For example, $\color{#bfe3b4} At_1$ refers to the `Infantry` attack class of the unit.

$\color{yellow} Ar_i$ is quantity of the armour class with id $i$ for the defending unit. For example, $\color{yellow} Ar_{19}$ refers to the `Unique Unit` armour class of the defending unit. Note that if an armour class does not exist for the defending unit, use the base armour value in that case!

(Note that the ids for every armour class in the game can be found in the table under the topic 3.2.)

then:

$$
\text{dmg} =  \color{#ff6961} \text{max}( \color{#a66fb5} \sum\limits_{\forall \; i \; \in D}^{}
                               \color{#add8e6}\text{max}( \color{#bfe3b4} At_i-\color{yellow} Ar_i, \; \color{white} 0 \color{#add8e6}), \;
                               \color{white} 1 \color{#ff6961})
$$

Note: $\color{#a66fb5} \sum\limits_{\forall \; i \; \in D}^{}$ means, add up something $for$ $all$ $i$ $in$ $D$

### 3.4. Explanation Using Code

The case of the War Elephant attacking the Halberdier:

| **Attack Classes War Elephant**| **Quantity**|      | **Armour Classes Halberdier**  | **Quantity**|
| :-----------                   | :---------: |      | :-----------                   | :---------: |
| -                              |   -         |      | 1  (Infantry)                  |   2         |
| -                              |   -         |      | 3  (Base Pierce)               |   2         |
| 4  (Base Melee)                |   15        |      | 4  (Base Melee)                |   1         |
| 11  (All buildings)            |   7         |      | -                              |   -         |
| 13  (Stone Defense)            |   7         |      | -                              |   -         |
| 21 (Standard Buildings)        |   0         |      | -                              |   -         |
| -                              |   -         |      | 27 (Unique Units)              |   0         |
| -                              |   -         |      | 31 (Unused)                    |   0         |

Here you can see all the attack classes listed out for the War Elephant and the armour classes listed out for the Halberdier.

For calculating the total amount of damage that this unupgraded War Elephant deals to the unupgraded Halberdier, we go through these steps given below:

1. Identify the damage classes that are in common for the attacking unit's attack class list and the defending unit's armour class list.
2. For each damage class that is in common, subtract the armour of the defending unit from the attack of the attacking unit. Round up to 0 if you get a negative value.
3. For each attack class of the attacking unit for which there is no armour class for the defending unit, we use the base armour value to calculate how much attack needs to be dealt.
4. Now add all of the differences found above. Round up to 1 if you get 0.
5. The value thus obtained is the damage that the War Elephant deals to the Halberdier.

The only common damage class is `Base Melee (4)` (highlighted in the table above)

This means that the damage that the War Elephant does to the Halberdier is simply given by $\text{dmg} = 15-1 = 14$ (The calculation with the base armour is not shown here since no attack class has an attack of more than 1000 to overecome the base armour)

```py
damage = 0
# 1. for each attack_class that the attacking unit has
for attack_class, attack in attacker.attack_classes:
    used_armour = target.base_armour # almost always 1000
    if attack_class in targer.armour_classes:
		used_armour = target.armour_classes[attack_class]

# 2. Find the difference of the attacker's attack and the target's armour.
# If the difference is negative, round it up to 0. Add this value to damage

	damage = damage + max(attack - used_armour, 0)

# if the total damage is less than 1, round it up to 1
damage = max(damage, 1)
```

Every unit in the game always has the `Base Pierce (3)`, `Base Melee (4)` and `Leitis (31)` damage classes.

Every unique unit in the game always has the `19 (Unitque Unit)` armour class. (Can you think of where this armour class is used? Hint: which unit deals bonus damage to all unique units?)

In this manner, the damage classes determine which units deal bonus damage to other units

### 3.5. Answering the questions

After having gone through this, can you now think of the answers to the questions posed at the beginning of the guide?

Q1. How does a Cataphract only take +16 damage from Halbderdiers instead of the full 32?

Q2. How to give bonus damage or bonus damage resistance to a particular unit?

Before you move on to read the answers, try and think about how these bonus damages might be being achieved.

A1. Cataphracts have 16 armour on the `Cavalry (8)` armour class, which is the `attack class` used by Halberdiers for extra 32 damage vs regular cavalry.

A2. One of the unused damage classes can be used for this purpose. Giving the desired unit attack on an unused class and giving the target unit 0 armour on the same unused class will produce the effect of the desired unit doing bonus damage to the target unit.

### 3.6. The Sicilian 50% Bonus Damage Reduction

The damage from all classes except the `Base Pierce (3)`, `Base Melee (4)` and `Leitis (31)` is multiplied by 0.5 before it is added to the total damage for Sicilian units. This property of bonus damage resistance is controlled by the [Bonus Damage Resist](../attributes/attributes/#24-bonus-damage-resistance "Jump to: Game Mechanics > Attributes > Bonus Damage Resist") attribute of a unit. (Yes, every single unit can have a different value for this)

---

