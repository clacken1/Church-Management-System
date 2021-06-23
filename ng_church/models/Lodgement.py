#! /user/bin/python3.8
#-*- encoding: utf-8 -*-

from datetime import date
from odoo import api, fields, models
from .helper import parish
from odoo.exceptions import UserError, ValidationError, MissingError


class Lodgement(models.Model):
    """Lodgement class."""

    _name = 'ng_church.lodgement'

    def _get_default_journal(self):
        if self.env.user.company_id.transit_journal.id:
            return self.env.user.company_id.transit_journal.id
        raise UserError('Church Transist account is not set.')
    name = fields.Char(string='Name', default='Church Lodgement')
    date = fields.Date(string='Date', required=True)
    amount = fields.Float(string='Amount', required=True)
    description = fields.Text(string='Note', required=True)
    church_id = fields.Many2one('res.company', default=parish)
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 domain=[('type', '=', 'bank')], required=True)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')],
                             copy=False, default='draft')

    @api.constrains('amount')
    def _check_valid_amount(self):
        if self.amount < 1:
            raise ValidationError(
                'Please enter a valid amount of money {} amount can\'t be post for lodgement'.format(self.amount))

    def _prepare_account_move(self):
        account_move = self.env['account.move']
        if self.journal_id.default_debit_account_id.id is False:
            raise MissingError(
                '{} default debit and credit are not set.'.format(self.journal_id.name))
        account_move = account_move.create(
            {
                'journal_id': self.journal_id.id, 
                'date': self.date,
                'state': 'draft',
                'type': 'entry',
                'currency_id': self.env.user.company_id.currency_id.id,
                'extract_state': 'done',
                'line_ids': [
                    (0, 0, {
                        'name': self.description,
                        'account_id': self.env.user.company_id.transit_account.id,
                        'credit': abs(self.amount),
                    }),
                    (0, 0, {
                        'name': self.description,
                        'account_id': self.journal_id.default_debit_account_id.id,
                        'debit': abs(self.amount),
                    })
                ]
            }
        )
        return account_move
     
    def lodge(self):
        """lodgement."""
        move = self._prepare_account_move()
        move.post()
        self.name = move.name
        self.state = move.state
