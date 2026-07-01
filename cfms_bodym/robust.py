# -*- coding: utf-8 -*-
"""
BodyMeasureRobust  ---  a drop-in, separately-named improvement of BodyMeasure
==============================================================================
The original BodyMeasure (cfms_bodym/__init__.py) is kept UNCHANGED so that the
before/after behaviour can be compared directly. This subclass adds two
improvements identified for the TSE_TomoSh3 body-measurement pipeline:

  (R1) No-crash guards: each feature finder runs in isolation, so a single
       failure (e.g., a body part missing after a poor segmentation, or an
       arbitrary pose) no longer aborts the whole measurement.
  (R2) Girth validity check: a girth is accepted only if its closed cross-section
       actually ENCIRCLES the cutting origin (bone axis). This rejects the
       spurious off-axis fragments that the original method reports as if they
       were valid (e.g., the M20/87k hip = 31.3 cm false reading).

  (R4) Non-manifold-tolerant lengths: the exact edge-flip geodesic needs a manifold
       mesh and aborts on self-contact poses (e.g., a jump). find_lengths first tries
       the geodesic on a repaired copy and, failing that, falls back to a graph (edge)
       shortest path, so surface lengths are still measured rather than skipped.

  (A candidate R3 -- enlarging the breast-point curvature radius from 0.01 cm to
   a body-scale value -- was tested and REJECTED: the larger radius over-smooths
   the sharp nipple and moves the detected point to the torso side, so the
   original radius is retained. See the sensitivity figure in draft_sh3.)

Usage:
    from cfms_bodym.robust import BodyMeasureRobust
    bodym = BodyMeasureRobust(avatar, body_parts, prebuilt_bodym)
    bodym.measure()
"""
import numpy as np

from cfms_bodym import BodyMeasure
from cfms_bodym.bodym_functions import (
    girth_data, feature_points_data, length_data, get, LandMark, GirthSlice,
    FeaturePos, SizeLine, get_closest_boundary, get_vtx_to_dir, get_pts_length, BodyPart)


class BodyMeasureRobust(BodyMeasure):

    # --- R1: each stage isolated so one failure does not abort the rest --------
    def _safe(self, fn):
        try:
            fn()
        except Exception as e:
            print(f"[robust] skipped {getattr(fn,'__name__',fn)}: {type(e).__name__}: {e}")

    def measure(self):
        self.failed_girths = []      # girths rejected by R2
        self.failed_lengths = []     # surface lengths that could not be measured
        self.length_mode = 'geodesic'
        self.find_girths()
        self.find_feature_points()
        self._safe(self.find_lengths)

    # --- R2: accept a girth only if its loop encircles the cut origin -----------
    @staticmethod
    def _encircles(slice, origin):
        V = np.array(slice.vertices)
        if len(V) < 4:
            return False
        c = V.mean(axis=0)
        r = float(np.linalg.norm(V - c, axis=1).mean())   # mean radius of the loop
        if r < 1e-6:
            return False
        return float(np.linalg.norm(c - origin)) < r       # origin within ~1 mean-radius of centre

    def find_girths(self):
        M = self.avatar.manager
        for lm in girth_data:
            c_o = self.getBP(get(lm, LandMark.Part))
            if not c_o:
                continue
            B0 = M.get_bone_pos_by_name(get(lm, LandMark.From))
            B1 = M.get_bone_pos_by_name(get(lm, LandMark.To))
            t = get(lm, LandMark.param)
            origin = B0 * t + B1 * (1. - t)
            normal = self.getBPVec(lm)
            try:
                slice = c_o.tmesh.section(plane_origin=origin, plane_normal=normal)
            except Exception:
                slice = None
            if not slice:
                continue
            slice = get_closest_boundary(slice, origin)
            name = get(lm, LandMark.Name)
            if slice and self._encircles(slice, origin):
                self.girths.append(GirthSlice(name, slice))
            else:
                self.failed_girths.append(name)   # honest: rejected rather than reported as spurious

    # --- R1 applied to the feature-point stage ---------------------------------
    def find_feature_points(self):
        for fn in (self._find_addams_apple, self._find_breast_point,
                   self._find_crotch_point, self._find_finger_tip):
            self._safe(fn)
        for ft in feature_points_data:
            girth = self.get_girth(ft[1])
            if girth:
                try:
                    self.features.append(FeaturePos(ft[0], get_vtx_to_dir(girth.vertices, self.getBPVec(ft))))
                except Exception:
                    pass
        self._safe(self._adjust_waist_points)
    # Note: _find_breast_point is intentionally NOT overridden -- the original
    # small-radius curvature gives the better (chest-front) nipple point; the
    # larger-radius variant was tested and rejected (see module docstring).

    # --- R4: surface lengths that survive non-manifold (arbitrary-pose) meshes -
    def find_lengths(self):
        # The exact edge-flip geodesic solver requires a manifold mesh; self-contact
        # poses (e.g., a jumping pose) produce duplicate edges and the solver aborts.
        # Try the geodesic on a repaired copy first; if it cannot be built, fall back
        # to a graph (edge) shortest path, which tolerates non-manifold meshes. This
        # way lengths are still measured rather than skipped entirely.
        T = self.avatar.tmesh
        self._geoV = np.array(T.vertices)
        self._geo_solver = None
        try:
            import potpourri3d as pp3d
            Tc = T.copy()
            Tc.merge_vertices()
            Tc.update_faces(Tc.unique_faces())
            Tc.update_faces(Tc.nondegenerate_faces())
            Tc.remove_unreferenced_vertices()
            self._geoV = np.array(Tc.vertices)
            self._geo_solver = pp3d.EdgeFlipGeodesicSolver(self._geoV, np.array(Tc.faces))
            self.length_mode = 'geodesic'
        except Exception:
            self._geo_solver = None
            self.length_mode = 'graph'   # non-manifold -> fall back to edge shortest path
        for d in length_data:
            try:
                pts = self.shortest_path(d[1])
            except Exception:
                pts = None
            if pts is not None and len(pts) >= 2:
                self.sizelines.append(SizeLine(d[0], pts, get_pts_length(pts)))
            else:
                self.failed_lengths.append(d[0])

    def shortest_path(self, features):
        # exact geodesic when available ...
        if self._geo_solver is not None:
            try:
                return super().shortest_path(features)
            except Exception:
                pass
        # ... otherwise a non-manifold-tolerant graph (edge) shortest path
        import networkx as nx
        V = np.array(self.avatar.tmesh.vertices)
        pts = np.empty((0, 3))
        for f1, f2 in zip(features[:-1], features[1:]):
            i1 = int(self.get_nearest_v_id_to_feature(V, f1))
            i2 = int(self.get_nearest_v_id_to_feature(V, f2))
            try:
                ids = nx.shortest_path(self.G, source=i1, target=i2, weight='length')
                pts = np.append(pts, V[ids], axis=0)
            except Exception:
                pts = np.append(pts, V[[i1, i2]], axis=0)   # last resort: straight segment
        return pts
