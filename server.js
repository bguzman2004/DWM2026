const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const { ApolloServer, gql, UserInputError } = require('apollo-server-express');
const Platillo = require('./models/platillo');

mongoose.connect('mongodb://localhost:27017/dwm2026');

const typeDefs = gql`
    type Platillo {
        id: ID
        nombre: String!
        categoria: String!
        precio: Int!
        descripcion: String
    }
    input PlatilloInput{
        nombre: String!
        categoria: String!
        precio: Int!
        descripcion: String
    }
    type Alert{
        message: String
    }
    type Query{
        getPlatillos(limit: Int, offset: Int): [Platillo]
        getPlatilloById(id: ID!): Platillo
    }
    type Mutation{
        addPlatillo(input: PlatilloInput): Platillo
        updPlatillo(id: ID!, input: PlatilloInput): Platillo
        delPlatillo(id: ID!): Alert
    }
`;

const LIMITE_MAXIMO = 50;

const resolvers = {
    Query: {
        async getPlatillos(obj, {limit, offset}){
            // Paginación: evita traer toda la colección de una sola consulta.
            const take = Math.min(limit ?? 20, LIMITE_MAXIMO);
            const skip = offset ?? 0;
            const platillos = await Platillo.find().skip(skip).limit(take);
            return platillos;
        },
        async getPlatilloById(obj, {id}){
            const platilloBus = await Platillo.findById(id);
            if (platilloBus == null){
                return null;
            } else {
                return platilloBus;
            }
        }
    },
    Mutation: {
        async addPlatillo(obj, {input}){
            if (!input.nombre || !input.nombre.trim()){
                throw new UserInputError("El nombre del platillo es obligatorio.");
            }
            if (input.precio <= 0){
                throw new UserInputError("El precio debe ser mayor a 0.");
            }
            const platillo = new Platillo(input);
            await platillo.save();
            return platillo;
        },
        async updPlatillo(obj, {id, input}){
            if (input.precio !== undefined && input.precio <= 0){
                throw new UserInputError("El precio debe ser mayor a 0.");
            }
            // { new: true } para devolver el documento ya actualizado, no el anterior.
            const platillo = await Platillo.findByIdAndUpdate(id, input, {new: true});
            if (platillo == null){
                throw new UserInputError("No existe un platillo con ese id.");
            }
            return platillo;
        },
        async delPlatillo(obj, {id}){
            const eliminado = await Platillo.findByIdAndDelete(id);
            if (eliminado == null){
                return {
                    message: "No existía un platillo con ese id"
                }
            }
            return {
                message: "Platillo Eliminado"
            }
        }
    }
};

const app = express();
app.use(cors());

const corsOption = {
    origin: "http://localhost:8090",
    credentials: false
};

async function startServer(){
    const apolloServer = new ApolloServer({typeDefs, resolvers, corsOption});
    await apolloServer.start();
    apolloServer.applyMiddleware({app, cors: false});
}
startServer();

app.listen(8090, function(){
    console.log("Graphql iniciado");
});