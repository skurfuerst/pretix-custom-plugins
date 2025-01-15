import unittest
from types import SimpleNamespace

from MyInvoiceRenderer import MyInvoiceRenderer
from pretix.base.models import InvoiceLine


class TestInvoiceGrouping(unittest.TestCase):
    def test_basic_mainproduct_grouping(self):
        input = [
            SimpleNamespace(
                description="Conference Ticket Regular",
                tax_rate=19,
                tax_name="USt",
                net_value=100,
                gross_value=119,
                subevent_id=None,
                event_date_from="2024-04-01",
                event_date_to="2024-04-02",
                item=SimpleNamespace(
                    meta_data={
                        'INVOICE_IS_MAINPRODUCT': "1",
                        'INVOICE_MAINPRODUCT_NAME': "Neos Conference Ticket - Category A",
                        'INVOICE_MAINPRODUCT_NAME_PRIORITY': "10"
                    }
                )
            ),
            SimpleNamespace(
                description="+ Zimmer Mi-Fr",
                tax_rate=19,
                tax_name="USt",
                net_value=50,
                gross_value=59,
                subevent_id=None,
                event_date_from="2024-04-01",
                event_date_to="2024-04-02",
                item=SimpleNamespace(
                    meta_data={
                        'INVOICE_IS_SUBPRODUCT': "1",
                        'INVOICE_MAINPRODUCT_NAME': "Neos Conference Ticket - Category B",
                        'INVOICE_MAINPRODUCT_NAME_PRIORITY': "20"
                    }
                )
            ),
            SimpleNamespace(
                description="+ Neos von 0 auf 100 Workshop",
                tax_rate=19,
                tax_name="USt",
                net_value=200,
                gross_value=245,
                subevent_id=None,
                event_date_from="2024-04-01",
                event_date_to="2024-04-02",
                item=SimpleNamespace(
                    meta_data={
                    }
                )
            )
        ]

        expected = [
            ("Neos Conference Ticket - Category B", 19, "USt", 150, 178, 1),
            ("+ Neos von 0 auf 100 Workshop", 19, "USt", 200, 245, 1)
        ]
        self.check_result(expected, input)

    def test_products_without_metadata_passed_through(self):
        input = [
            SimpleNamespace(
                description="Conference Ticket Regular",
                tax_rate=19,
                tax_name="USt",
                net_value=100,
                gross_value=119,
                subevent_id=None,
                event_date_from="2024-04-01",
                event_date_to="2024-04-02",
                item=SimpleNamespace(
                    meta_data={
                    }
                )
            ),
            SimpleNamespace(
                description="+ Neos von 0 auf 100 Workshop",
                tax_rate=19,
                tax_name="USt",
                net_value=200,
                gross_value=245,
                subevent_id=None,
                event_date_from="2024-04-01",
                event_date_to="2024-04-02",
                item=SimpleNamespace(
                    meta_data={
                    }
                )
            )
        ]

        expected = [
            ("Conference Ticket Regular", 19, "USt", 100, 119, 1),
            ("+ Neos von 0 auf 100 Workshop", 19, "USt", 200, 245, 1)
        ]
        self.check_result(expected, input)

    def test_error_if_subproduct_has_no_mainproduct_before(self):
        input = [
            SimpleNamespace(
                description="+ Zimmer Mi-Fr",
                tax_rate=19,
                tax_name="USt",
                net_value=50,
                gross_value=59,
                subevent_id=None,
                event_date_from="2024-04-01",
                event_date_to="2024-04-02",
                item=SimpleNamespace(
                    meta_data={
                        'INVOICE_IS_SUBPRODUCT': "1",
                        'INVOICE_MAINPRODUCT_NAME': "Neos Conference Ticket - Category B",
                        'INVOICE_MAINPRODUCT_NAME_PRIORITY': "20"
                    }
                )
            ),
        ]
        expected = [
        ]
        try:
            self.check_result(expected, input)
        except:
            pass
        else:
            self.assertFalse(True, "we expected an exception, but did not find any.")

    def test_multiple_tickets_sold(self):
        regularConfTicket = SimpleNamespace(
            description="Conference Ticket Regular",
            tax_rate=19,
            tax_name="USt",
            net_value=100,
            gross_value=119,
            subevent_id=None,
            event_date_from="2024-04-01",
            event_date_to="2024-04-02",
            item=SimpleNamespace(
                meta_data={
                    'INVOICE_IS_MAINPRODUCT': "1",
                    'INVOICE_MAINPRODUCT_NAME': "Neos Conference Ticket - Category A",
                    'INVOICE_MAINPRODUCT_NAME_PRIORITY': "10"
                }
            )
        )
        zimmerMiFr = SimpleNamespace(
            description="+ Zimmer Mi-Fr",
            tax_rate=19,
            tax_name="USt",
            net_value=50,
            gross_value=59,
            subevent_id=None,
            event_date_from="2024-04-01",
            event_date_to="2024-04-02",
            item=SimpleNamespace(
                meta_data={
                    'INVOICE_IS_SUBPRODUCT': "1",
                    'INVOICE_MAINPRODUCT_NAME': "Neos Conference Ticket - Category B",
                    'INVOICE_MAINPRODUCT_NAME_PRIORITY': "20"
                }
            )
        )
        neos_workshop = SimpleNamespace(
            description="+ Neos von 0 auf 100 Workshop",
            tax_rate=19,
            tax_name="USt",
            net_value=200,
            gross_value=245,
            subevent_id=None,
            event_date_from="2024-04-01",
            event_date_to="2024-04-02",
            item=SimpleNamespace(
                meta_data={
                }
            )
        )
        input = [
            regularConfTicket,

            regularConfTicket,
            zimmerMiFr,
            neos_workshop,

            regularConfTicket,
            neos_workshop,
            zimmerMiFr,

            regularConfTicket,
            zimmerMiFr,

            regularConfTicket,

            regularConfTicket,
            neos_workshop,
        ]

        expected = [
            ("Neos Conference Ticket - Category A", 19, "USt", 100, 119, 1),

            ("Neos Conference Ticket - Category B", 19, "USt", 150, 178, 1),
            ("+ Neos von 0 auf 100 Workshop", 19, "USt", 200, 245, 1),

            ("Neos Conference Ticket - Category B", 19, "USt", 150, 178, 1),
            ("+ Neos von 0 auf 100 Workshop", 19, "USt", 200, 245, 1),

            ("Neos Conference Ticket - Category B", 19, "USt", 150, 178, 1),

            ("Neos Conference Ticket - Category A", 19, "USt", 100, 119, 1),

            ("Neos Conference Ticket - Category A", 19, "USt", 100, 119, 1),
            ("+ Neos von 0 auf 100 Workshop", 19, "USt", 200, 245, 1),
        ]
        self.check_result(expected, input)


    def check_result(self, expected, input):
        i = 0
        for (description, tax_rate, tax_name, net_value, gross_value, *ignored), lines in MyInvoiceRenderer._invoice_lines(input):
            lines = list(lines)
            (expected_description, expected_tax_rate, expected_tax_name, expected_net_value, expected_gross_value,
             expected_no_lines) = expected[i]
            self.assertEquals(description, expected_description, "description mismatch")
            self.assertEquals(tax_name, expected_tax_name, "tax_name mismatch")
            self.assertEquals(net_value, expected_net_value, "net_value mismatch")
            self.assertEquals(gross_value, expected_gross_value, "gross_value mismatch")
            self.assertEquals(len(lines), expected_no_lines, "line count mismatch")
            i = i + 1
        self.assertEquals(i, len(expected), "Count does not match")


if __name__ == '__main__':
    unittest.main()
