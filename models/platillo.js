const mongoose = require('mongoose');
const platilloSchema = mongoose.Schema({
    nombre: String,
    categoria: String,
    precio: Number,
    descripcion: String
});

module.exports = mongoose.model('Platillo', platilloSchema);