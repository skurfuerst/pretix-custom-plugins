from collections import defaultdict
from decimal import Decimal
from itertools import groupby
from typing import Iterator

import vat_moss.exchange_rates
from django.db.models import Sum
from django.utils.formats import date_format, localize
from django.utils.translation import (
    get_language, gettext, gettext_lazy, pgettext,
)
from reportlab.lib import colors, pagesizes
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, NextPageTemplate,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from pretix.base.decimal import round_decimal
from pretix.base.models import Event, Invoice, Order, OrderPayment, InvoiceLine
from pretix.base.services.currencies import SOURCE_NAMES
from pretix.base.templatetags.money import money_filter

from pretix.base.invoice import Modern1Renderer, PaidMarker


class MyInvoiceRenderer(Modern1Renderer):
    identifier = 'neoscon-special'
    verbose_name = "NeosCon Special Sum"

    @staticmethod
    def _invoice_lines(invoice_lines: Iterator[InvoiceLine]):

        rewritten_invoice_lines = []

        related_mainproduct_idx = -1
        related_mainproduct_prio = 0
        i = -1
        for line in invoice_lines:
            prio = -1
            if line.item and "INVOICE_MAINPRODUCT_NAME_PRIORITY" in line.item.meta_data:
                prio = line.item.meta_data["INVOICE_MAINPRODUCT_NAME_PRIORITY"]

            if line.item and "INVOICE_IS_SUBPRODUCT" in line.item.meta_data and line.item.meta_data["INVOICE_IS_SUBPRODUCT"] == "1":
                # is sub product, merge with recent main product
                if related_mainproduct_idx == -1:
                    raise Exception("Main product must have been found beforehand")

                res_to_modify = list(rewritten_invoice_lines[related_mainproduct_idx][0])

                if "INVOICE_MAINPRODUCT_NAME" in line.item.meta_data:
                    if prio > related_mainproduct_prio:
                        # override description
                        related_mainproduct_prio = prio
                        res_to_modify[0] = line.item.meta_data["INVOICE_MAINPRODUCT_NAME"]

                # tax_rate
                if res_to_modify[1] != line.tax_rate:
                    raise Exception("Tax rate must match for subproducts")

                # tax_name
                if res_to_modify[2] != line.tax_name:
                    raise Exception("Tax name must match for subproducts")

                # sum net_value
                res_to_modify[3] += line.net_value
                # sum gross_value
                res_to_modify[4] += line.gross_value

                rewritten_invoice_lines[related_mainproduct_idx] = tuple([res_to_modify, rewritten_invoice_lines[related_mainproduct_idx][1]])

            else:
                # no sub-product
                description = line.description
                if line.item and "INVOICE_MAINPRODUCT_NAME" in line.item.meta_data:
                    description = line.item.meta_data["INVOICE_MAINPRODUCT_NAME"]
                rewritten_invoice_lines.append((
                    (description, line.tax_rate, line.tax_name, line.net_value, line.gross_value,
                     line.subevent_id,
                     line.event_date_from, line.event_date_to),
                    [line]  # lines
                ))

                i = i + 1

                if line.item and "INVOICE_IS_MAINPRODUCT" in line.item.meta_data and line.item.meta_data[
                    "INVOICE_IS_MAINPRODUCT"] == "1":
                    related_mainproduct_idx = i
                    related_mainproduct_prio = prio

        return rewritten_invoice_lines

    # CHANGES are marked with BEGIN MODIFICATION.
    def _get_story(self, doc):
        has_taxes = any(il.tax_value for il in self.invoice.lines.all()) or self.invoice.reverse_charge

        story = [
            NextPageTemplate('FirstPage'),
            Paragraph(
                self._normalize(
                    pgettext('invoice', 'Tax Invoice') if str(self.invoice.invoice_from_country) == 'AU'
                    else pgettext('invoice', 'Invoice')
                ) if not self.invoice.is_cancellation else self._normalize(pgettext('invoice', 'Cancellation')),
                self.stylesheet['Heading1']
            ),
            Spacer(1, 5 * mm),
            NextPageTemplate('OtherPages'),
        ]
        story += self._get_intro()

        taxvalue_map = defaultdict(Decimal)
        grossvalue_map = defaultdict(Decimal)

        tstyledata = [
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), self.font_regular),
            ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ('FONTNAME', (0, -1), (-1, -1), self.font_bold),
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
        ]
        if has_taxes:
            tdata = [(
                Paragraph(self._normalize(pgettext('invoice', 'Description')), self.stylesheet['Bold']),
                Paragraph(self._normalize(pgettext('invoice', 'Qty')), self.stylesheet['BoldRightNoSplit']),
                Paragraph(self._normalize(pgettext('invoice', 'Tax rate')), self.stylesheet['BoldRightNoSplit']),
                Paragraph(self._normalize(pgettext('invoice', 'Net')), self.stylesheet['BoldRightNoSplit']),
                Paragraph(self._normalize(pgettext('invoice', 'Gross')), self.stylesheet['BoldRightNoSplit']),
            )]
        else:
            tdata = [(
                Paragraph(self._normalize(pgettext('invoice', 'Description')), self.stylesheet['BoldRight']),
                Paragraph(self._normalize(pgettext('invoice', 'Qty')), self.stylesheet['BoldRightNoSplit']),
                Paragraph(self._normalize(pgettext('invoice', 'Amount')), self.stylesheet['BoldRightNoSplit']),
            )]

        # BEGIN MODIFICATION
        #import pydevd_pycharm
        #pydevd_pycharm.settrace('localhost', port=12345, stdoutToServer=True, stderrToServer=True)
        # def _group_key(line):
        # line.description
        #    return (line.description, line.tax_rate, line.tax_name, line.net_value, line.gross_value, line.subevent_id,
        #            line.event_date_from, line.event_date_to)

        total = Decimal('0.00')

        # for (description, tax_rate, tax_name, net_value, gross_value, *ignored), lines in groupby(self.invoice.lines.all(), key=_group_key):
        for (description, tax_rate, tax_name, net_value, gross_value, *ignored), lines in self._invoice_lines(self.invoice.lines.all()):
            # END MODIFICATION
            lines = list(lines)
            if has_taxes:
                if len(lines) > 1:
                    single_price_line = pgettext('invoice',
                                                 'Single price: {net_price} net / {gross_price} gross').format(
                        net_price=money_filter(net_value, self.invoice.event.currency),
                        gross_price=money_filter(gross_value, self.invoice.event.currency),
                    )
                    description = description + "\n" + single_price_line
                tdata.append((
                    Paragraph(
                        self._clean_text(description, tags=['br']),
                        self.stylesheet['Normal']
                    ),
                    str(len(lines)),
                    localize(tax_rate) + " %",
                    Paragraph(money_filter(net_value * len(lines), self.invoice.event.currency).replace('\xa0', ' '),
                              self.stylesheet['NormalRight']),
                    Paragraph(money_filter(gross_value * len(lines), self.invoice.event.currency).replace('\xa0', ' '),
                              self.stylesheet['NormalRight']),
                ))
            else:
                if len(lines) > 1:
                    single_price_line = pgettext('invoice', 'Single price: {price}').format(
                        price=money_filter(gross_value, self.invoice.event.currency),
                    )
                    description = description + "\n" + single_price_line
                tdata.append((
                    Paragraph(
                        self._clean_text(description, tags=['br']),
                        self.stylesheet['Normal']
                    ),
                    str(len(lines)),
                    Paragraph(money_filter(gross_value * len(lines), self.invoice.event.currency).replace('\xa0', ' '),
                              self.stylesheet['NormalRight']),
                ))
            taxvalue_map[tax_rate, tax_name] += (gross_value - net_value) * len(lines)
            grossvalue_map[tax_rate, tax_name] += gross_value * len(lines)
            total += gross_value * len(lines)

        if has_taxes:
            tdata.append([
                Paragraph(self._normalize(pgettext('invoice', 'Invoice total')), self.stylesheet['Bold']), '', '', '',
                money_filter(total, self.invoice.event.currency)
            ])
            colwidths = [a * doc.width for a in (.50, .05, .15, .15, .15)]
        else:
            tdata.append([
                Paragraph(self._normalize(pgettext('invoice', 'Invoice total')), self.stylesheet['Bold']), '',
                money_filter(total, self.invoice.event.currency)
            ])
            colwidths = [a * doc.width for a in (.65, .20, .15)]

        if not self.invoice.is_cancellation:
            if self.invoice.event.settings.invoice_show_payments and self.invoice.order.status == Order.STATUS_PENDING:
                pending_sum = self.invoice.order.pending_sum
                if pending_sum != total:
                    tdata.append(
                        [Paragraph(self._normalize(pgettext('invoice', 'Received payments')),
                                   self.stylesheet['Normal'])] +
                        (['', '', ''] if has_taxes else ['']) +
                        [money_filter(pending_sum - total, self.invoice.event.currency)]
                    )
                    tdata.append(
                        [Paragraph(self._normalize(pgettext('invoice', 'Outstanding payments')),
                                   self.stylesheet['Bold'])] +
                        (['', '', ''] if has_taxes else ['']) +
                        [money_filter(pending_sum, self.invoice.event.currency)]
                    )
                    tstyledata += [
                        ('FONTNAME', (0, len(tdata) - 3), (-1, len(tdata) - 3), self.font_bold),
                    ]
            elif self.invoice.event.settings.invoice_show_payments and self.invoice.order.payments.filter(
                    state__in=(OrderPayment.PAYMENT_STATE_CONFIRMED, OrderPayment.PAYMENT_STATE_REFUNDED),
                    provider='giftcard'
            ).exists():
                giftcard_sum = self.invoice.order.payments.filter(
                    state__in=(OrderPayment.PAYMENT_STATE_CONFIRMED, OrderPayment.PAYMENT_STATE_REFUNDED),
                    provider='giftcard'
                ).aggregate(
                    s=Sum('amount')
                )['s'] or Decimal('0.00')
                tdata.append(
                    [Paragraph(self._normalize(pgettext('invoice', 'Paid by gift card')), self.stylesheet['Normal'])] +
                    (['', '', ''] if has_taxes else ['']) +
                    [money_filter(giftcard_sum, self.invoice.event.currency)]
                )
                tdata.append(
                    [Paragraph(self._normalize(pgettext('invoice', 'Remaining amount')), self.stylesheet['Bold'])] +
                    (['', '', ''] if has_taxes else ['']) +
                    [money_filter(total - giftcard_sum, self.invoice.event.currency)]
                )
                tstyledata += [
                    ('FONTNAME', (0, len(tdata) - 3), (-1, len(tdata) - 3), self.font_bold),
                ]
            elif self.invoice.payment_provider_stamp:
                pm = PaidMarker(
                    text=self._normalize(self.invoice.payment_provider_stamp),
                    color=colors.HexColor(self.event.settings.theme_color_success),
                    font=self.font_bold,
                    size=16
                )
                tdata[-1][-2] = pm

        table = Table(tdata, colWidths=colwidths, repeatRows=1)
        table.setStyle(TableStyle(tstyledata))
        story.append(table)

        story.append(Spacer(1, 10 * mm))

        if self.invoice.payment_provider_text:
            story.append(Paragraph(
                self._normalize(self.invoice.payment_provider_text),
                self.stylesheet['Normal']
            ))

        if self.invoice.payment_provider_text and self.invoice.additional_text:
            story.append(Spacer(1, 3 * mm))

        if self.invoice.additional_text:
            story.append(Paragraph(
                self._clean_text(self.invoice.additional_text, tags=['br']),
                self.stylesheet['Normal']
            ))
            story.append(Spacer(1, 5 * mm))

        tstyledata = [
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (-1, -1), self.font_regular),
        ]
        thead = [
            Paragraph(self._normalize(pgettext('invoice', 'Tax rate')), self.stylesheet['Fineprint']),
            Paragraph(self._normalize(pgettext('invoice', 'Net value')), self.stylesheet['FineprintRight']),
            Paragraph(self._normalize(pgettext('invoice', 'Gross value')), self.stylesheet['FineprintRight']),
            Paragraph(self._normalize(pgettext('invoice', 'Tax')), self.stylesheet['FineprintRight']),
            ''
        ]
        tdata = [thead]

        for idx, gross in grossvalue_map.items():
            rate, name = idx
            if rate == 0:
                continue
            tax = taxvalue_map[idx]
            tdata.append([
                Paragraph(self._normalize(localize(rate) + " % " + name), self.stylesheet['Fineprint']),
                money_filter(gross - tax, self.invoice.event.currency),
                money_filter(gross, self.invoice.event.currency),
                money_filter(tax, self.invoice.event.currency),
                ''
            ])

        def fmt(val):
            try:
                return vat_moss.exchange_rates.format(val, self.invoice.foreign_currency_display)
            except ValueError:
                return localize(val) + ' ' + self.invoice.foreign_currency_display

        if len(tdata) > 1 and has_taxes:
            colwidths = [a * doc.width for a in (.25, .15, .15, .15, .3)]
            table = Table(tdata, colWidths=colwidths, repeatRows=2, hAlign=TA_LEFT)
            table.setStyle(TableStyle(tstyledata))
            story.append(Spacer(5 * mm, 5 * mm))
            story.append(KeepTogether([
                Paragraph(self._normalize(pgettext('invoice', 'Included taxes')), self.stylesheet['FineprintHeading']),
                table
            ]))

            if self.invoice.foreign_currency_display and self.invoice.foreign_currency_rate:
                tdata = [thead]

                for idx, gross in grossvalue_map.items():
                    rate, name = idx
                    if rate == 0:
                        continue
                    tax = taxvalue_map[idx]
                    gross = round_decimal(gross * self.invoice.foreign_currency_rate)
                    tax = round_decimal(tax * self.invoice.foreign_currency_rate)
                    net = gross - tax

                    tdata.append([
                        Paragraph(self._normalize(localize(rate) + " % " + name), self.stylesheet['Fineprint']),
                        fmt(net), fmt(gross), fmt(tax), ''
                    ])

                table = Table(tdata, colWidths=colwidths, repeatRows=2, hAlign=TA_LEFT)
                table.setStyle(TableStyle(tstyledata))

                story.append(KeepTogether([
                    Spacer(1, height=2 * mm),
                    Paragraph(
                        self._normalize(pgettext(
                            'invoice', 'Using the conversion rate of 1:{rate} as published by the {authority} on '
                                       '{date}, this corresponds to:'
                        ).format(rate=localize(self.invoice.foreign_currency_rate),
                                 authority=SOURCE_NAMES.get(self.invoice.foreign_currency_source, "?"),
                                 date=date_format(self.invoice.foreign_currency_rate_date, "SHORT_DATE_FORMAT"))),
                        self.stylesheet['Fineprint']
                    ),
                    Spacer(1, height=3 * mm),
                    table
                ]))
        elif self.invoice.foreign_currency_display and self.invoice.foreign_currency_rate:
            foreign_total = round_decimal(total * self.invoice.foreign_currency_rate)
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph(self._normalize(
                pgettext(
                    'invoice', 'Using the conversion rate of 1:{rate} as published by the {authority} on '
                               '{date}, the invoice total corresponds to {total}.'
                ).format(rate=localize(self.invoice.foreign_currency_rate),
                         date=date_format(self.invoice.foreign_currency_rate_date, "SHORT_DATE_FORMAT"),
                         authority=SOURCE_NAMES.get(self.invoice.foreign_currency_source, "?"),
                         total=fmt(foreign_total))),
                self.stylesheet['Fineprint']
            ))

        return story
