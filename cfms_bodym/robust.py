# -*- coding: utf-8 -*-
"""
BodyMeasureRobust  ---  a drop-in, separately-named improvement of BodyMeasure
==============================================================================
The original BodyMeasure (cfms_bodym/__init__.py) is kept UNCHANGED so that the
before/after behaviour can be compared directly. This subclass adds these
improvements identified for the TSE_TomoSh3 body-measurement pipeline:

  (R1) No-crash guards: each feature finder runs in isolation, so a single
       failure (e.g., a body part missing after a poor segmentation, or an
       arbitrary pose) no longer aborts the whole measurement.
  (R2) Girth validity check, in two steps.
       (a) The cross-section must contain a CLOSED loop. The original pipeline
           takes whatever get_closest_boundary() returns, which for a section made
           only of open polylines is an open polyline, and reports its length as a
           girth (the M20/87k hip = 21.1 cm false reading is exactly that).
       (b) The chosen closed loop must ENCLOSE the cutting origin (bone axis).
           Two interchangeable tests are implemented: the centroid/mean-radius
           proxy of the manuscript (eq. 2) and the exact winding number of the loop
           about the origin in the cutting plane. VALIDITY selects the test.
       Every girth gets a status so that the failure reason is reported, not just
       the absence of a value:
           accepted | no_part | no_section | no_closed_loop | rejected
  (R4) Non-manifold-tolerant lengths: the exact edge-flip geodesic needs a manifold
       mesh and aborts on self-contact poses (e.g., a jump). find_lengths first tries
       the geodesic on a repaired copy and, failing that, falls back to a graph (edge)
       shortest path, so surface lengths are still measured rather than skipped.

  (A candidate R3 -- enlarging the breast-point curvature radius from 0.01 cm to
   a body-scale value -- was tested and REJECTED: the larger radius over-smooths
   the sharp nipple and moves the detected point to the torso side, so the
   original radius is retained. See the sensitivity figure in draft_sh5.)

2026-09-11 correction (peer-review round). Until this date step (a) was missing:
an open polyline could reach the enclosure test and, when its centroid happened to
lie within one mean radius of the origin, was accepted as a girth. On the jumping
mesh one of the sixteen "accepted" girths and on the synthetic bodies one to two of
the fifteen to seventeen were such open polylines. The counts reported before this
date therefore overstate acceptance; draft_sh5 uses the corrected counts.

Usage:
    from cfms_bodym.robust import BodyMeasureRobust
    bodym = BodyMeasureRobust(avatar, body_parts, prebuilt_bodym)
    bodym.measure()
"""
import numpy as np
import trimesh

from cfms_bodym import BodyMeasure
from cfms_bodym.bodym_functions import (
    girth_data, feature_points_data, length_data, get, LandMark, GirthSlice,
    FeaturePos, SizeLine, get_closest_boundary, get_vtx_to_dir, get_pts_length, BodyPart)


class BodyMeasureRobust(BodyMeasure):

    VALIDITY = 'centroid'    # 'centroid' = eq. (2) of the manuscript; 'winding' = exact winding number

    # --- R1: each stage isolated so one failure does not abort the rest --------
    def _safe(self, fn):
        try:
            fn()
        except Exception as e:
            print(f"[robust] skipped {getattr(fn,'__name__',fn)}: {type(e).__name__}: {e}")

    def measure(self):
        self.failed_girths = []      # closed loops rejected by the enclosure test (R2b)
        self.unclosed_girths = []    # section had no closed loop (R2a)
        self.missing_girths = []     # body part absent, or the plane misses the part
        self.girth_status = {}       # name -> accepted | no_part | no_section | no_closed_loop | rejected
        self.failed_lengths = []     # surface lengths that could not be measured
        self.length_mode = 'geodesic'
        self.find_girths()
        self.find_feature_points()
        self._safe(self.find_lengths)

    # --- R2: validity of a cross-section ---------------------------------------
    @staticmethod
    def _closed_loops(slice):
        """(entity, ordered loop points) for every closed entity of a section."""
        out = []
        for ent in slice.entities:
            if getattr(ent, 'closed', False) and len(ent.nodes) >= 3:
                out.append((ent, np.asarray(slice.vertices[ent.nodes[:, 0]], dtype=float)))
        return out

    @staticmethod
    def _encircles(points_or_slice, origin):
        """Eq. (2): the loop centroid lies within one mean radius of the cut origin."""
        V = np.asarray(points_or_slice.vertices if hasattr(points_or_slice, 'vertices')
                       else points_or_slice, dtype=float)
        if len(V) < 4:
            return False
        c = V.mean(axis=0)
        r = float(np.linalg.norm(V - c, axis=1).mean())   # mean radius of the loop
        if r < 1e-6:
            return False
        return float(np.linalg.norm(c - origin)) < r       # origin within ~1 mean-radius of centre

    @staticmethod
    def _winding_number(P, origin, normal):
        """Winding number of the ordered loop P about `origin`, in the plane with `normal`.
        Sum of signed angles between consecutive vertices: O(N), same cost as eq. (2)."""
        n = np.asarray(normal, dtype=float); n = n / np.linalg.norm(n)
        e1 = np.cross(n, [1., 0., 0.])
        if np.linalg.norm(e1) < 1e-6:
            e1 = np.cross(n, [0., 1., 0.])
        e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
        Q = np.column_stack(((P - origin) @ e1, (P - origin) @ e2))
        Q2 = np.roll(Q, -1, axis=0)
        ang = np.arctan2(Q[:, 0] * Q2[:, 1] - Q[:, 1] * Q2[:, 0], (Q * Q2).sum(axis=1))
        return float(ang.sum() / (2.0 * np.pi))

    def _valid_loop(self, P, origin, normal):
        if self.VALIDITY == 'winding':
            return abs(round(self._winding_number(P, origin, normal))) >= 1
        return self._encircles(P, origin)

    def find_girths(self):
        M = self.avatar.manager
        for lm in girth_data:
            name = get(lm, LandMark.Name)
            c_o = self.getBP(get(lm, LandMark.Part))
            if not c_o:
                self.girth_status[name] = 'no_part'; self.missing_girths.append(name); continue
            B0 = M.get_bone_pos_by_name(get(lm, LandMark.From))
            B1 = M.get_bone_pos_by_name(get(lm, LandMark.To))
            t = get(lm, LandMark.param)
            origin = np.asarray(B0, dtype=float) * t + np.asarray(B1, dtype=float) * (1. - t)
            normal = self.getBPVec(lm)
            try:
                slice = c_o.tmesh.section(plane_origin=origin, plane_normal=normal)
            except Exception:
                slice = None
            if not slice:
                self.girth_status[name] = 'no_section'; self.missing_girths.append(name); continue
            loops = self._closed_loops(slice)
            if not loops:                                       # R2a: open polylines only
                self.girth_status[name] = 'no_closed_loop'; self.unclosed_girths.append(name); continue
            # same selection rule as the original: the closed loop nearest to the origin
            ent, P = min(loops, key=lambda ep: np.linalg.norm(ep[1].mean(axis=0) - origin))
            if self._valid_loop(P, origin, normal):             # R2b: must enclose the origin
                chosen = trimesh.path.Path3D(entities=[ent], vertices=slice.vertices)
                chosen.remove_unreferenced_vertices()
                self.girths.append(GirthSlice(name, chosen))
                self.girth_status[name] = 'accepted'
            else:
                self.girth_status[name] = 'rejected'
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
        return self.graph_path(features)

    def graph_path(self, features):
        """Edge (graph) shortest path through the feature points; an upper bound of the geodesic."""
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
