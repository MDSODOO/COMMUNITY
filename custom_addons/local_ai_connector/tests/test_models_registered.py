# -*- coding: utf-8 -*-
"""
Guardia contra modelos huerfanos: todo archivo de `models/` que declare un
`_name` debe estar importado en `models/__init__.py`, y su modelo debe existir
de verdad en el registro de Odoo.

Por que existe este test: el 2026-07-31 se encontro que
`models/vision_identification.py` (modelo `local.ai.vision.identification`)
NO estaba importado en `models/__init__.py`, pese a que
`services/vision_product_identifier.py` lo usa. El endpoint
`/ai/identify_product_from_photo` lanzaba KeyError al registrar su log, y el
log de Odoo acumulo 40 errores `Missing model` sin que nadie lo notara.
Era una regresion: la funcionalidad habia estado instalada y en uso.

Este test habria cazado esa regresion en el momento de introducirla.
"""
import ast
import os

from odoo.tests import tagged, TransactionCase

# Tag obligatorio: sin 'post_install' el test corre antes de que ciertos
# datos base terminen de cargar y falla de formas dificiles de diagnosticar.
@tagged('post_install', '-at_install')
class TestModelsRegistered(TransactionCase):

    def _models_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')

    def _declared_models(self):
        """Devuelve {nombre_archivo_sin_ext: [_name declarados]} leyendo el AST.

        Se usa AST y no import dinamico a proposito: importar el modulo
        registraria la clase y enmascararia justo el fallo que se busca.
        """
        found = {}
        for filename in sorted(os.listdir(self._models_dir())):
            if not filename.endswith('.py') or filename == '__init__.py':
                continue
            path = os.path.join(self._models_dir(), filename)
            with open(path, 'r', encoding='utf-8') as fh:
                tree = ast.parse(fh.read(), filename=path)
            names = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for stmt in node.body:
                    if not isinstance(stmt, ast.Assign):
                        continue
                    for target in stmt.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id == '_name'
                            and isinstance(stmt.value, ast.Constant)
                            and isinstance(stmt.value.value, str)
                        ):
                            names.append(stmt.value.value)
            if names:
                found[filename[:-3]] = names
        return found

    def _imported_submodules(self):
        """Nombres importados en models/__init__.py, leidos del AST."""
        init_path = os.path.join(self._models_dir(), '__init__.py')
        with open(init_path, 'r', encoding='utf-8') as fh:
            tree = ast.parse(fh.read(), filename=init_path)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module is None:
                # from . import a, b
                imported.update(alias.name for alias in node.names)
        return imported

    def test_every_model_file_is_imported(self):
        """Ningun archivo de models/ con `_name` puede quedar sin importar."""
        declared = self._declared_models()
        self.assertTrue(
            declared,
            "No se detecto ningun modelo en models/ — revisa el parser del test, "
            "no es plausible que el modulo no declare ninguno.",
        )
        imported = self._imported_submodules()
        missing = sorted(set(declared) - imported)
        self.assertFalse(
            missing,
            "Estos archivos de models/ declaran un _name pero NO estan importados "
            "en models/__init__.py, asi que Odoo nunca los carga: %s. "
            "Cualquier env['<modelo>'] sobre ellos lanzara KeyError." % (
                ', '.join('%s.py (%s)' % (m, ', '.join(declared[m])) for m in missing),
            ),
        )

    def test_every_declared_model_exists_in_registry(self):
        """Cada `_name` declarado debe resolverse en el registro de Odoo."""
        declared = self._declared_models()
        absent = []
        for filename, names in declared.items():
            for name in names:
                if name not in self.env:
                    absent.append('%s (en %s.py)' % (name, filename))
        self.assertFalse(
            absent,
            "Estos modelos se declaran en el codigo pero no existen en el "
            "registro de Odoo: %s" % ', '.join(sorted(absent)),
        )

    def test_every_declared_model_has_access_rules(self):
        """Un modelo sin reglas de acceso es ilegible desde la interfaz.

        El servicio puede escribir con .sudo(), pero si nadie puede leer, la
        trazabilidad que promete el modelo no sirve de nada.
        """
        declared = self._declared_models()
        Access = self.env['ir.model.access'].sudo()
        without_rules = []
        for filename, names in declared.items():
            for name in names:
                if name not in self.env:
                    continue  # ya lo reporta el test anterior
                if not Access.search_count([('model_id.model', '=', name)]):
                    without_rules.append('%s (en %s.py)' % (name, filename))
        self.assertFalse(
            without_rules,
            "Estos modelos no tienen ninguna regla en ir.model.access.csv: %s" % (
                ', '.join(sorted(without_rules)),
            ),
        )
