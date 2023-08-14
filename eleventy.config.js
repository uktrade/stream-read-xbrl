const govukEleventyPlugin = require('@x-govuk/govuk-eleventy-plugin')

module.exports = function(eleventyConfig) {
  // Register the plugin
  eleventyConfig.addPlugin(govukEleventyPlugin, {
    fontFamily: 'system-ui, sans-serif',
    icons: {
      shortcut: '/assets/dit-favicon.png'
    },
    header: {
      organisationName: 'DBT',
      organisationLogo: '<img class="app-header__logotype--large" src="/assets/dit-logo.png" height="35" width="62">',
      productName: 'stream-read-xbrl',
    }
  })

  eleventyConfig.addPassthroughCopy('./docs/assets')
  eleventyConfig.addPassthroughCopy('./docs/CNAME')

  return {
    dataTemplateEngine: 'njk',
    htmlTemplateEngine: 'njk',
    markdownTemplateEngine: 'njk',
    dir: {
      // Use layouts from the plugin
      input: 'docs',
      layouts: '../node_modules/@x-govuk/govuk-eleventy-plugin/layouts'
    }
  }
};
