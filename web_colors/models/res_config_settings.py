import re
import base64

from odoo import api, fields, models
from odoo.tools import misc

from odoo.addons.base.models.assetsbundle import EXTENSIONS


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    # ----------------------------------------------------------
    # Properties
    # ----------------------------------------------------------

    @property
    def COLOR_FIELDS(self):
        return [
            'color_brand',
            'color_primary',
            'color_success',
            'color_info',
            'color_warning',
            'color_danger',
        ]
        
    @property
    def COLOR_ASSET_LIGHT_URL(self):
        return '/web_colors/static/src/scss/colors_light.scss'
        
    @property
    def COLOR_BUNDLE_LIGHT_NAME(self):
        return 'web._assets_primary_variables'
        
    @property
    def COLOR_ASSET_DARK_URL(self):
        return '/web_colors/static/src/scss/colors_dark.scss'
        
    @property
    def COLOR_BUNDLE_DARK_NAME(self):
        return 'web.assets_web_dark'

    #----------------------------------------------------------
    # Fields Light Mode
    #----------------------------------------------------------
    
    color_brand_light = fields.Char(
        string='Brand Light Color'
    )
    
    color_primary_light = fields.Char(
        string='Primary Light Color'
    )
    
    color_success_light = fields.Char(
        string='Success Light Color'
    )
    
    color_info_light = fields.Char(
        string='Info Light Color'
    )
    
    color_warning_light = fields.Char(
        string='Warning Light Color'
    )
    
    color_danger_light = fields.Char(
        string='Danger Light Color'
    )

    #----------------------------------------------------------
    # Fields Dark Mode
    #----------------------------------------------------------
    
    color_brand_dark = fields.Char(
        string='Brand Dark Color'
    )
    
    color_primary_dark = fields.Char(
        string='Primary Dark Color'
    )
    
    color_success_dark = fields.Char(
        string='Success Dark Color'
    )
    
    color_info_dark = fields.Char(
        string='Info Dark Color'
    )
    
    color_warning_dark = fields.Char(
        string='Warning Dark Color'
    )
    
    color_danger_dark = fields.Char(
        string='Danger Dark Color'
    )
    
    #----------------------------------------------------------
    # Helper
    #----------------------------------------------------------
    
    def _get_light_color_values(self):
        # return self.env['web_editor.assets'].get_color_variables_values(
        return self.get_color_variables_values(
            self.COLOR_ASSET_LIGHT_URL, 
            self.COLOR_BUNDLE_LIGHT_NAME,
            self.COLOR_FIELDS
        )
        
    def _get_dark_color_values(self):
        # return self.env['web_editor.assets'].get_color_variables_values(
        return self.get_color_variables_values(
            self.COLOR_ASSET_DARK_URL, 
            self.COLOR_BUNDLE_DARK_NAME,
            self.COLOR_FIELDS
        )
        
    def _set_light_color_values(self, values):
        colors = self._get_light_color_values()
        for var, value in colors.items():
            values[f'{var}_light'] = value
        return values
        
    def _set_dark_color_values(self, values):
        colors = self._get_dark_color_values()
        for var, value in colors.items():
            values[f'{var}_dark'] = value
        return values
    
    def _detect_light_color_change(self):
        colors = self._get_light_color_values()
        return any(
            self[f'{var}_light'] != val
            for var, val in colors.items()
        )
        
    def _detect_dark_color_change(self):
        colors = self._get_dark_color_values()
        return any(
            self[f'{var}_dark'] != val
            for var, val in colors.items()
        )
        
    def _replace_light_color_values(self):
        variables = [
            {
                'name': field, 
                'value': self[f'{field}_light']
            }
            for field in self.COLOR_FIELDS
        ]
        # return self.env['web_editor.assets'].replace_color_variables_values(
        return self.replace_color_variables_values(
            self.COLOR_ASSET_LIGHT_URL, 
            self.COLOR_BUNDLE_LIGHT_NAME,
            variables
        )
        
    def _replace_dark_color_values(self):
        variables = [
            {
                'name': field, 
                'value': self[f'{field}_dark']
            }
            for field in self.COLOR_FIELDS
        ]
        # return self.env['web_editor.assets'].replace_color_variables_values(
        return self.replace_color_variables_values(
            self.COLOR_ASSET_DARK_URL, 
            self.COLOR_BUNDLE_DARK_NAME,
            variables
        )
    
    def _reset_light_color_assets(self):
        # self.env['web_editor.assets'].reset_color_asset(
        self.reset_color_asset(
            self.COLOR_ASSET_LIGHT_URL, 
            self.COLOR_BUNDLE_LIGHT_NAME,
        )
        
    def _reset_dark_color_assets(self):
        # self.env['web_editor.assets'].reset_asset(
        self.reset_color_asset(
            self.COLOR_ASSET_DARK_URL, 
            self.COLOR_BUNDLE_DARK_NAME,
        )

    #----------------------------------------------------------
    # Action
    #----------------------------------------------------------

    def action_reset_light_color_assets(self):
        self._reset_light_color_assets()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_reset_dark_color_assets(self):
        self._reset_dark_color_assets()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------

    def get_values(self):
        res = super().get_values()
        res = self._set_light_color_values(res)
        res = self._set_dark_color_values(res)
        return res

    def set_values(self):
        res = super().set_values()
        if self._detect_light_color_change():
            self._replace_light_color_values()
        if self._detect_dark_color_change():
            self._replace_dark_color_values()
        return res




    # _inherit = 'web_editor.assets'

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    @api.model
    def _get_colors_attachment(self, custom_url):
        return self.env['ir.attachment'].search([
            ('url', '=', custom_url)
        ])

    @api.model
    def _get_colors_asset(self, custom_url):
        return self.env['ir.asset'].search([
            ('path', 'like', custom_url)
        ])

    @api.model
    def _get_colors_from_url(self, url, bundle):
        custom_url = self.env["web_editor.assets"]._make_custom_asset_url(url, bundle)
        url_info = self.env["web_editor.assets"]._get_data_from_url(custom_url)
        if url_info['customized']:
            attachment = self._get_colors_attachment(
                custom_url
            )
            if attachment:
                return base64.b64decode(attachment.datas)
        with misc.file_open(url.strip('/'), 'rb', filter_ext=EXTENSIONS) as f:
            return f.read()

    def _get_color_variable(self, content, variable):
        value = re.search(fr'\$mk_{variable}\:?\s(.*?);', content)
        return value and value.group(1)

    def _get_color_variables(self, content, variables):
        return {
            var: self._get_color_variable(content, var) 
            for var in variables
        }

    def _replace_color_variables(self, content, variables):
        for variable in variables:
            content = re.sub(
                fr'{variable["name"]}\:?\s(.*?);', 
                f'{variable["name"]}: {variable["value"]};', 
                content
            )
        return content

    @api.model
    def _save_color_asset(self, url, bundle, content):
        custom_url = self.env["web_editor.assets"]._make_custom_asset_url(url, bundle)
        asset_url = url[1:] if url.startswith(('/', '\\')) else url
        datas = base64.b64encode((content or "\n").encode("utf-8"))
        custom_attachment = self._get_colors_attachment(
            custom_url
        )
        if custom_attachment:
            custom_attachment.write({"datas": datas})
            self.env.registry.clear_cache('assets')
        else:
            attachment_values = {
                'name': url.split("/")[-1],
                'type': "binary",
                'mimetype': 'text/scss',
                'datas': datas,
                'url': custom_url,
            }
            asset_values = {
                'path': custom_url,
                'target': url,
                'directive': 'replace',
            }
            target_asset = self._get_colors_asset(
                asset_url
            )
            if target_asset:
                asset_values['name'] = '%s override' % target_asset.name
                asset_values['bundle'] = target_asset.bundle
                asset_values['sequence'] = target_asset.sequence
            else:
                asset_values['name'] = '%s: replace %s' % (
                    bundle, custom_url.split('/')[-1]
                )
                asset_values['bundle'] = self.env['ir.asset']._get_related_bundle(
                    url, bundle
                )
            self.env['ir.attachment'].create(attachment_values)
            self.env['ir.asset'].create(asset_values)

    # ----------------------------------------------------------
    # Functions
    # ----------------------------------------------------------

    def get_color_variables_values(self, url, bundle, variables):
        content = self._get_colors_from_url(url, bundle)
        return self._get_color_variables(
            content.decode('utf-8'), variables
        )
    
    def replace_color_variables_values(self, url, bundle, variables):
        original = self._get_colors_from_url(url, bundle).decode('utf-8')
        content = self._replace_color_variables(original, variables)
        self._save_color_asset(url, bundle, content)

    def reset_color_asset(self, url, bundle):
        custom_url = self.env["web_editor.assets"]._make_custom_asset_url(url, bundle)
        self._get_colors_attachment(custom_url).unlink()
        self._get_colors_asset(custom_url).unlink()
