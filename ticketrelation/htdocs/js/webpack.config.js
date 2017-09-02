module.exports = {
    entry: './select_tickets.js',
    output: {
        filename: 'select_tickets_bundle.js',
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader',
            }
        ]
    },
    resolve: {
        alias: {
            'vue$': 'vue/dist/vue.esm'
        }
    }
};