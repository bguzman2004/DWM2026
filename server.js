const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const { ApolloServer, gql } = require('apollo-server-express');
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
        getPlatillos: [Platillo]
        getPlatilloById(id: ID!): Platillo
    }
    type Mutation{
        addPlatillo(input: PlatilloInput): Platillo
        updPlatillo(id: ID!, input: PlatilloInput): Platillo
        delPlatillo(id: ID!): Alert
    }
`;

const resolvers = {
    Query: {
        async getPlatillos(obj){
            const platillos = await Platillo.find();
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
            const platillo = new Platillo(input);
            await platillo.save();
            return platillo;
        },
        async updPlatillo(obj, {id, input}){
            const platillo = await Platillo.findByIdAndUpdate(id, input);
            return platillo;
        },
        async delPlatillo(obj, {id}){
            await Platillo.deleteOne({_id: id});
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