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

from ..input import get_vertices_and_normals
from .method_util import assign_emissive_material


class LP_OT_Skin(bpy.types.Operator):
    """Modal object selection with a ray cast"""
    bl_idname = 'semagnum.lp_skin'
    bl_label = 'Light Paint Skin'
    bl_options = {'REGISTER', 'UNDO'}

    distance: bpy.props.FloatProperty(
        name='Distance',
        description='Distance from the drawing along the vertex normal',
        min=0.001,
        default=5.0,
        unit='LENGTH'
    )

    skin_radius: bpy.props.FloatProperty(
        name='Skin radius',
        description='Radius of skin modifier',
        min=0.001,
        default=0.1,
        unit='LENGTH'
    )

    is_smooth: bpy.props.BoolProperty(
        name='Smooth',
        description='If checked, skin modifier will set smooth faces',
        options=set(),
        default=True
    )

    pre_subdiv: bpy.props.IntProperty(
        name='Pre-skin Subdivision',
        description='Subdivision level before skin modifier - will smooth the wire path',
        min=0,
        default=2,
        soft_max=4,
    )

    post_subdiv: bpy.props.IntProperty(
        name='Post-skin subdivision',
        description='Subdivision level after skin modifier - will smooth the wire itself',
        min=0,
        default=2,
        soft_max=4,
    )

    emit_value: bpy.props.FloatProperty(
        name='Emit Value',
        description='Emission shader\'s emit value',
        min=0.001,
        default=2.0,
    )

    @classmethod
    def poll(cls, context):
        return hasattr(context.active_annotation_layer,
                       'active_frame') and context.active_annotation_layer.active_frame.strokes

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        mesh = bpy.data.meshes.new("ConvexHullLight")
        obj = bpy.data.objects.new(mesh.name, mesh)
        col = context.collection
        col.objects.link(obj)
        context.view_layer.objects.active = obj

        vertices, normals = get_vertices_and_normals(context)

        projected_vertices = [v + (norm * self.distance)
                              for v, norm in zip(vertices, normals)]
        stroke_edge_indices = [(start_idx, end_idx)
                               for start_idx, end_idx in zip(range(len(projected_vertices) - 1),
                                                             range(1, len(projected_vertices)))]

        mesh.from_pydata(projected_vertices, stroke_edge_indices, [])

        bpy.ops.object.modifier_add(type='SUBSURF')
        bpy.ops.object.modifier_add(type='SKIN')
        bpy.ops.object.modifier_add(type='SUBSURF')

        obj.modifiers["Subdivision"].levels = self.pre_subdiv
        obj.modifiers["Subdivision"].render_levels = self.pre_subdiv
        obj.modifiers["Skin"].use_smooth_shade = self.is_smooth
        obj.modifiers["Subdivision.001"].levels = self.post_subdiv
        obj.modifiers["Subdivision.001"].render_levels = self.post_subdiv

        for v in obj.data.skin_vertices[0].data:
            v.radius = [self.skin_radius, self.skin_radius]
        # obj.data.skin_vertices[0].data.foreach_set('radius', radii)

        # assign emissive material to it
        assign_emissive_material(obj, self.emit_value)

        return {'FINISHED'}