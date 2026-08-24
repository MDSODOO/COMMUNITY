# -*- coding: utf-8 -*-


def migrate(cr, version):
    # Renombrar los logins duplicados de 'tecnologias@medicinedepotsureste.mx'
    # Dejaremos intacto el que tenga el ID mas bajo (el original) y al resto le
    # agregaremos '_dup_id'.
    cr.execute("""
        UPDATE res_users
        SET login = login || '_dup_' || id::text
        WHERE login = 'tecnologias@medicinedepotsureste.mx'
        AND id != (
            SELECT MIN(id)
            FROM res_users
            WHERE login = 'tecnologias@medicinedepotsureste.mx'
        );
    """)
