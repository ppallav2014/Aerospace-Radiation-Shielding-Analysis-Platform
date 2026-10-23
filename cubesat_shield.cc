/**
 * @file cubesat_shield.cc
 * @brief High Performance Monte Carlo Space Radiation Shielding & Transport Engine
 * @details Simulates energetic particle transport (protons, electrons, alphas, gammas) 
 *          through multi material satellite shielding and silicon payload cores using Geant4.
 * 
 * @author Piyush Pallav
 * @email ppallav2014@gmail.com
 */

#include "G4RunManagerFactory.hh"
#include "G4MTRunManager.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VUserActionInitialization.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"
#include "G4NistManager.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "FTFP_BERT.hh"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4AutoLock.hh"

#include <fstream>
#include <iostream>

// Global Mission & Beam Parameters (Overridden via command line arguments)
G4String gMaterial = "G4_Al";
G4double gThickness = 5.0 * mm;
G4double gEnergy    = 50.0 * MeV;
G4String gParticle  = "proton";

// Thread-safety lock and file output streams for telemetry logging
namespace { G4Mutex fileMutex = G4MUTEX_INITIALIZER; }
std::ofstream resFile, trackFile, secFile;

/**
 * @class DetectorConstruction
 * @brief Defines the nested box-in-box satellite geometry (World -> Shield -> Payload).
 */
class DetectorConstruction : public G4VUserDetectorConstruction {
public:
    G4VPhysicalVolume* Construct() override {
        G4NistManager* nist = G4NistManager::Instance();
        
        // 1. World Volume (Vacuum Galactic Space)
        G4Material* vacuum = nist->FindOrBuildMaterial("G4_Galactic");
        G4Box* solidWorld = new G4Box("World", 15 * cm, 15 * cm, 15 * cm);
        G4LogicalVolume* logicWorld = new G4LogicalVolume(solidWorld, vacuum, "World");
        G4VPhysicalVolume* physWorld = new G4PVPlacement(nullptr, G4ThreeVector(), logicWorld, "World", nullptr, false, 0);

        // 2. Outer Shielding Layer (Configurable Material and Thickness)
        G4Material* shieldMat = nist->FindOrBuildMaterial(gMaterial);
        G4Box* solidShield = new G4Box("Shield", 5 * cm, 5 * cm, 5 * cm);
        G4LogicalVolume* logicShield = new G4LogicalVolume(solidShield, shieldMat, "Shield");
        new G4PVPlacement(nullptr, G4ThreeVector(), logicShield, "Shield", logicWorld, false, 0);

        // 3. Inner Sensitive Electronics Payload (Silicon Core)
        G4double payloadSize = 5 * cm - gThickness; 
        G4Material* siMat = nist->FindOrBuildMaterial("G4_Si");
        G4Box* solidPayload = new G4Box("Payload", payloadSize, payloadSize, payloadSize);
        G4LogicalVolume* logicPayload = new G4LogicalVolume(solidPayload, siMat, "Payload");
        new G4PVPlacement(nullptr, G4ThreeVector(), logicPayload, "Payload", logicShield, false, 0);

        return physWorld;
    }
};

/**
 * @class PrimaryGenerator
 * @brief Configures the primary particle gun source upstream of the satellite model.
 */
class PrimaryGenerator : public G4VUserPrimaryGeneratorAction {
    G4ParticleGun* fParticleGun;
public:
    PrimaryGenerator() {
        fParticleGun = new G4ParticleGun(1);
        fParticleGun->SetParticleDefinition(G4ParticleTable::GetParticleTable()->FindParticle(gParticle));
    }
    
    ~PrimaryGenerator() { 
        delete fParticleGun; 
    }
    
    void GeneratePrimaries(G4Event* anEvent) override {
        fParticleGun->SetParticleEnergy(gEnergy);
        fParticleGun->SetParticlePosition(G4ThreeVector(0, 0, -12 * cm));
        fParticleGun->SetParticleMomentumDirection(G4ThreeVector(0, 0, 1));
        fParticleGun->GeneratePrimaryVertex(anEvent);
    }
};

/**
 * @class SteppingAction
 * @brief Intercepts particle steps to extract tracks, energy deposits, and secondary cascades.
 */
class SteppingAction : public G4UserSteppingAction {
public:
    void UserSteppingAction(const G4Step* step) override {
        G4int eventID = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
        G4Track* track = step->GetTrack();
        G4String partName = track->GetDefinition()->GetParticleName();
        G4double kinEnergy = track->GetKineticEnergy() / MeV;

        G4LogicalVolume* volume = step->GetPreStepPoint()->GetTouchableHandle()->GetVolume()->GetLogicalVolume();
        G4String volName = volume->GetName();

        // Ensure safe multi-threaded file writing
        G4AutoLock lock(&fileMutex);

        // Capture newly generated secondary particles on their initial step
        if (track->GetCurrentStepNumber() == 1 && track->GetParentID() > 0) {
            secFile << partName << "," << kinEnergy << "," << volName << "\n";
        }

        // Sample trajectory coordinates for the 3D visualizer (limited to first 200 events for performance)
        if (eventID < 200) {
            G4ThreeVector pos = step->GetPostStepPoint()->GetPosition();
            trackFile << eventID << "," << track->GetTrackID() << "," 
                      << pos.x() / mm << "," << pos.y() / mm << "," << pos.z() / mm << "," << partName << "\n";
        }

        // Record energy deposition hits inside the sensitive silicon payload core
        if (volName == "Payload") {
            G4double edep = step->GetTotalEnergyDeposit();
            if (edep > 0) {
                resFile << eventID << "," << (edep / MeV) << "," << partName << "\n";
            }
        }
        
        lock.Unlock();
    }
};

/**
 * @class ActionInitialization
 * @brief Wires user action classes into the Geant4 execution runtime.
 */
class ActionInitialization : public G4VUserActionInitialization {
public:
    void BuildForMaster() const override {} 
    
    void Build() const override {
        SetUserAction(new PrimaryGenerator());
        SetUserAction(new SteppingAction());
    }
};

/**
 * @brief Main execution entry point for the simulation engine.
 */
int main(int argc, char** argv) {
    // Parse command line inputs if passed from the Python GUI frontend
    if (argc > 5) {
        gMaterial  = argv[1];
        gThickness = std::stod(argv[2]) * mm;
        gEnergy    = std::stod(argv[3]) * MeV;
        gParticle  = argv[5];
    }
    G4int events = (argc > 4) ? std::stoi(argv[4]) : 2000;

    // Open telemetry output streams with overwrite truncation
    resFile.open("results.csv", std::ios::trunc); 
    trackFile.open("tracks.csv", std::ios::trunc);
    secFile.open("secondaries.csv", std::ios::trunc);

    std::cout << "[SYSTEM] Initializing Geant4 Multi-Threaded Engine...\n";
    
    // Initialize Run Manager with FTFP_BERT physics standard list
    auto* runManager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::Default);
    runManager->SetUserInitialization(new DetectorConstruction());
    runManager->SetUserInitialization(new FTFP_BERT());
    runManager->SetUserInitialization(new ActionInitialization());
    runManager->Initialize();
    
    // Launch particle beam simulation loop
    runManager->BeamOn(events);
    
    // Clean shutdown and file stream closure
    delete runManager;
    resFile.close(); 
    trackFile.close(); 
    secFile.close();
    
    std::cout << "[SYSTEM] Geant4 Run Terminated Successfully.\n";
    return 0;
}
