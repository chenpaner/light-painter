#     Light Paint, Blender add-on that creates lights based on where the user paints.
#     Copyright (C) 2023 Spencer Magnusson
#     semagnum@gmail.com
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.


import bpy
from mathutils import Vector

from ..input import axis_prop, get_strokes, get_strokes_and_normals
from .method_util import has_strokes


class LP_OT_SpotLight(bpy.types.Operator):
    """Modal object selection with a ray cast"""
    bl_idname = 'semagnum.lp_light_spot'
    bl_label = 'Paint Spot Lamp'
    bl_options = {'REGISTER', 'UNDO'}

    axis: axis_prop()

    offset: bpy.props.FloatProperty(
        name='Offset',
        description='Light\'s offset from annotation along specified axis',
        min=0.0,
        default=1.0,
        unit='LENGTH'
    )

    power: bpy.props.FloatProperty(
        name='Power',
        description='Area light\'s emit value',
        min=0.001,
        default=10,
        subtype='POWER',
        unit='POWER'
    )

    min_size: bpy.props.FloatVectorProperty(
        name='Minimum size',
        description='Lamp size will be clamped to these minimum values',
        size=2,
        min=0.001,
        default=(0.01, 0.01),
        unit='LENGTH'
    )

    light_color: bpy.props.FloatVectorProperty(
        name='Color',
        size=3,
        default=(1.0, 1.0, 1.0),
        min=0.0,
        soft_max=1.0,
        subtype='COLOR'
    )

    @classmethod
    def poll(cls, context):
        return has_strokes(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'axis')
        layout.prop(self, 'offset')

        layout.separator()
        layout.label(text='Lamp')
        layout.prop(self, 'light_color')
        layout.prop(self, 'power')
        layout.prop(self, 'min_size')

    def execute(self, context):
        strokes = get_strokes_and_normals(context, self.axis, self.offset)
        vertices = tuple(v for stroke in strokes for v in stroke[0])
        normals = (n for stroke in strokes for n in stroke[1])

        # get average, negated normal
        avg_normal = sum(normals, start=Vector())
        avg_normal.normalize()
        avg_normal.negate()

        farthest_point = max((v.project(avg_normal).length_squared, v) for v in vertices)[1]

        projected_vertices = tuple(v + (farthest_point - v).project(avg_normal) for v in vertices)

        center = sum(projected_vertices, start=Vector()) / len(projected_vertices)
        rotation = Vector((0.0, 0.0, -1.0)).rotation_difference(avg_normal).to_euler()

        orig_strokes = get_strokes(context, self.axis, 0.0)
        orig_vertices = tuple(v for stroke in orig_strokes for v in stroke)
        orig_center = sum(orig_vertices, start=Vector()) / len(orig_vertices)
        centers_dir = (orig_center - center).normalized()
        spot_angle = 2 * max((v - center).normalized().angle(centers_dir)
                             for v in orig_vertices)

        bpy.ops.object.select_all(action='DESELECT')

        bpy.ops.object.light_add(type='SPOT', align='WORLD', location=center, rotation=rotation, scale=(1, 1, 1))

        # set light data properties
        context.object.data.color = self.light_color
        context.object.data.spot_size = spot_angle
        context.object.data.energy = self.power

        return {'FINISHED'}
